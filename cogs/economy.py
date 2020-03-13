import discord
from discord.ext import commands, timers
from main import connection
from utils.checks import commands_or_casino_only, owner_only
import asyncio


def remove_item(user, item, amount):
    inv = connection["inventory"].find_one(
        {"_id": user.id})
    if inv[item] == amount:
        connection["inventory"].update({"_id": user.id}, {"$unset": {item: 1}})
    else:
        connection["inventory"].update({"_id": user.id}, {"$inc": {item: -amount}})


class Economy(commands.Cog, command_attrs=dict(cooldown_after_parsing=True)):

    def __init__(self, bot):
        self.emoji = ":money_with_wings:"
        self.bot = bot
        self.con = connection
        self.timer_manager = timers.TimerManager(bot)

    @commands.command(usage="shop [page]", aliases=['market', 'store'])
    @commands.cooldown(1, 3, commands.BucketType.user)
    @commands_or_casino_only()
    async def shop(self, ctx, page: int = 1):
        """Zeigt den Shop"""

        shop = list(self.con["items"].find()) + list(self.con["tools"].find({"buy": {"$gt": 0}}))
        shop_items = []
        for item in shop:
            if item["buy"]:
                shop_items.append(item)
        shop_items.sort(key=lambda i: i["buy"])
        pages, b = divmod(len(shop_items), 5)
        if b != 0:
            pages += 1
        if page > pages or page < 1:
            await ctx.send(f'Seite nicht gefunden. Verfügbare Seiten: `{pages}`')
        else:
            def create_embed(page):
                embed = discord.Embed(color=0x983233, title=':convenience_store: Shop', description=f'Kaufe ein Item mit `{ctx.prefix}buy <item> [amount]`')
                embed.set_footer(text=f"Seite {page} von {pages}")
                for item in shop_items[(page - 1) * 5:(page - 1) * 5 + 5]:
                    embed.description += f"\n\n**{item['emoji']} {item['_id'].title()}: :inbox_tray: ${item['buy']} | :outbox_tray: ${item['sell']}**\n➼ {item['description']}"
                return embed

            menu = await ctx.send(embed=create_embed(page))
            if pages > 1:
                reactions = ['◀', '▶']
                for reaction in reactions:
                    await menu.add_reaction(reaction)

                def check(r, u):
                    return r.message.id == menu.id and u == ctx.author and str(r.emoji) in reactions

                while True:
                    try:
                        reaction, user = await ctx.bot.wait_for("reaction_add", check=check, timeout=60)
                    except asyncio.TimeoutError:
                        await menu.clear_reactions()
                        return
                    await menu.remove_reaction(reaction, user)
                    if str(reaction.emoji) == reactions[0] and page > 1:
                        page -= 1
                        await menu.edit(embed=create_embed(page))
                    elif str(reaction.emoji) == reactions[1] and page < pages:
                        page += 1
                        await menu.edit(embed=create_embed(page))

    @commands.command(usage='buy item=amount')
    @commands.cooldown(1, 3, commands.BucketType.user)
    @commands_or_casino_only()
    async def buy(self, ctx, *, args: str):
        """Kauft ein Item"""
        args = args.split("=")
        if len(args) == 1:
            args.append(1)
        elif len(args) != 2:
            await ctx.send(f"{ctx.author.mention} Wenn du mehrere Items auf einmal kaufen möchtest, benutze `{ctx.prefix}buy item=3`")
            return
        arg = args[0]
        amount = int(args[1])
        item = self.con["items"].find_one({"_id": arg, "buy": {"$gt": 0}})
        if not item:
            item = self.con["tools"].find_one({"_id": arg, "buy": {"$gt": 0}})
        if item:
            bal = self.con["stats"].find_one({"_id": ctx.author.id}, {"balance": 1})["balance"]
            if bal < item["buy"] * amount:
                await ctx.send(embed=discord.Embed(
                    color=discord.Color.red(),
                    title="Du hast nicht genügend Geld",
                    description=f"Du brauchst mindestens **{item['buy'] * amount}** :dollar:"
                ))
            else:
                self.con["inventory"].update({"_id": ctx.author.id}, {"$inc": {item["_id"]: amount}}, upsert=True)
                self.con["stats"].update({"_id": ctx.author.id}, {"$inc": {"balance": -(item["buy"] * amount)}})
                await ctx.send(embed=discord.Embed(
                    color=discord.Color.green(),
                    title="Transaktion erfolgreich",
                    description=f"Du hast **{amount}x {item['emoji']}** {item['_id'].title()} für **{item['buy'] * amount}** :dollar: gekauft"
                ))
        else:
            await ctx.send(f"{ctx.author.mention} Ich konnte dieses Item nicht finden oder es ist nicht käuflich.")

    @commands.command(usage='sell item=amount')
    @commands.cooldown(1, 3, commands.BucketType.user)
    @commands_or_casino_only()
    async def sell(self, ctx, *, args: str):
        """Verkauft ein Item"""
        if args.lower() == "all":
            inv = self.con["inventory"].find_one({"_id": ctx.author.id})
            if not inv:
                await ctx.send(embed=discord.Embed(
                    color=discord.Color.red(),
                    title="Verkaufen nicht möglich",
                    description=f"Du hast nicht genügend Items"
                ))
            else:
                msg = await ctx.send(f"{ctx.author.mention} Möchtest du wirklich **alle deine Items** verkaufen? (ja/nein)")
                try:
                    message = await ctx.bot.wait_for("message", check=lambda m: m.content.lower() in ["j", "ja", "y", "yes", "n", "nein", "no"] and m.author == ctx.author, timeout=30)
                except asyncio.TimeoutError:
                    await msg.edit(content="*Aktion abgebrochen*")
                    return
                if message.content.lower() in ["n", "nein", "no"]:
                    await msg.edit(content="*Aktion abgebrochen*")
                    return
                prices = {i["_id"]: i["sell"] for i in list(self.con["items"].find()) + list(self.con["tools"].find())}
                post = {}
                bal = 0
                i = 0
                a = False
                for item, count in inv.items():
                    if item != "_id":
                        post[item] = 1
                        i += count
                        bal += count * prices[item]
                self.con["stats"].update({"_id": ctx.author.id}, {"$inc": {"balance": bal}})
                self.con["inventory"].delete_one({"_id": ctx.author.id})
                await ctx.send(embed=discord.Embed(
                    color=discord.Color.green(),
                    title="Transaktion erfolgreich",
                    description=f"Du hast **{i}** Items für **{bal}** :dollar: verkauft"
                ))
        else:
            args = args.split("=")
            if len(args) == 1:
                args.append(1)
            elif len(args) != 2:
                await ctx.send(f"{ctx.author.mention} Wenn du mehrere Items auf einmal verkaufen möchtest, benutze `{ctx.prefix}sell item=3`")
                return
            arg = args[0]
            amount = int(args[1])
            item = self.con["items"].find_one({"_id": arg})
            if not item:
                item = self.con["tools"].find_one({"_id": arg})
            if item:
                count = self.con["inventory"].find_one(
                    {"_id": ctx.author.id, item["_id"]: {"$gt": amount - 1}})
                if not count:
                    await ctx.send(embed=discord.Embed(
                        color=discord.Color.red(),
                        title="Verkaufen nicht möglich",
                        description=f"Du hast nicht genügend Items"
                    ))
                else:
                    sell = item['sell'] * amount
                    self.con["stats"].update({"_id": ctx.author.id}, {"$inc": {"balance": sell}})
                    remove_item(ctx.author, item["_id"], amount)
                    await ctx.send(embed=discord.Embed(
                        color=discord.Color.green(),
                        title="Transaktion erfolgreich",
                        description=f"Du hast **{amount}x {item['emoji']}** {item['_id'].title()} für **{sell}** :dollar: verkauft"
                    ))
            else:
                await ctx.send(f"{ctx.author.mention} Ich konnte dieses Item nicht finden.")

    @commands.command(usage="inventory [page]", aliases=["inv"])
    @commands.cooldown(1, 3, commands.BucketType.user)
    @commands_or_casino_only()
    async def inventory(self, ctx, user: discord.User = None):
        """Zeigt dein Inventar"""
        if user is None:
            user = ctx.author
        results = self.con["inventory"].find_one({"_id": user.id})
        if not results:
            await ctx.send(embed=discord.Embed(
                color=discord.Color.red(),
                title=f":file_folder: {user.name}'s Inventar",
                description="Keine Items gefunden"
            ))
        else:
            items = {i["_id"]: i for i in list(self.con["items"].find())}
            tools = {i["_id"]: i for i in list(self.con["tools"].find())}
            value = 0
            for entry in results:
                if entry == "_id":
                    continue
                if entry in tools:
                    sell = tools[entry]["sell"]
                else:
                    sell = items[entry]["sell"]
                value += sell * results[entry]
            page = 1
            pages, b = divmod(len(results) - 1, 10)
            if b != 0:
                pages += 1

            def create_embed(p):
                embed = discord.Embed(color=0x983233,
                                      title=f":open_file_folder: {user.name}'s Inventar ({p}/{pages})",
                                      description="")
                for i, item in enumerate(results):
                    if item == "_id":
                        continue
                    elif i < (page - 1) * 10 + 1:
                        continue
                    elif i > (page - 1) * 10 + 10:
                        continue
                    elif results[item] == 0:
                        continue
                    else:
                        if item in tools:
                            emoji = tools[item]['emoji']
                        else:
                            emoji = items[item]['emoji']
                        embed.description += f"\n> **{results[item]}x {item.title()} {emoji}**"
                embed.set_footer(text=f"➼ Gesamtwert: {value}")
                return embed

            menu = await ctx.send(embed=create_embed(page))
            if pages > 1:
                reactions = ['◀', '▶']
                for reaction in reactions:
                    await menu.add_reaction(reaction)

                def check(r, u):
                    return r.message.id == menu.id and u == ctx.author and str(r.emoji) in reactions

                while True:
                    try:
                        reaction, user = await ctx.bot.wait_for("reaction_add", check=check, timeout=60)
                    except asyncio.TimeoutError:
                        await menu.delete()
                        return
                    await menu.remove_reaction(reaction, user)
                    if str(reaction.emoji) == reactions[0] and page > 1:
                        page -= 1
                        await menu.edit(embed=create_embed(page))
                    elif str(reaction.emoji) == reactions[1] and page < pages:
                        page += 1
                        await menu.edit(embed=create_embed(page))

    @commands.command(usage="additem <Item> <Emoji> <Preis> <Verkaufspreis> <Beschreibung>")
    @commands.cooldown(1, 3, commands.BucketType.user)
    @owner_only()
    async def additem(self, ctx, item: str, emoji: str, buy: int, sell: int, *, description: str):
        """Fügt ein Item hinzu"""
        post = {
            "emoji": emoji,
            "buy": buy,
            "sell": sell,
            "description": description
        }
        self.con["items"].update({"_id": item.lower()}, post, upsert=True)
        await ctx.send(embed=discord.Embed(
            color=discord.Color.green(),
            title="Item hinzugefügt",
            description=f"Name: **{item.title()}**\nEmoji: {emoji}\nPreis: **{buy}**\nVerkaufspreis: **{sell}**\nBeschreibung: {description}"
        ))

    @commands.command(usage="addtool <Name> <Emoji> <Verkaufspreis> <Beschreibung>")
    @commands.cooldown(1, 3, commands.BucketType.user)
    @owner_only()
    async def addtool(self, ctx, item: str, emoji: str, sell: int, *, description: str):
        """Fügt ein Item hinzu"""
        post = {
            "emoji": emoji,
            "sell": sell,
            "description": description
        }
        self.con["tools"].update({"_id": item.lower()}, post, upsert=True)
        await ctx.send(embed=discord.Embed(
            color=discord.Color.green(),
            title="Tool hinzugefügt",
            description=f"Name: **{item.title()}**\nEmoji: {emoji}\nVerkaufspreis: **{sell}**\nBeschreibung: {description}"
        ))

    @commands.command(usage="delitem <item>")
    @commands.cooldown(1, 3, commands.BucketType.user)
    @owner_only()
    async def delitem(self, ctx, item):
        """Entfernt ein Item"""
        self.con["items"].delete_one({"_id": item["_id"]})
        await ctx.send(embed=discord.Embed(
            color=discord.Color.green(),
            title="Item entfernt",
            description=f"Das Item **{item['_id'].title()}** wurde entfernt"
        ))

    @commands.command(usage="transferitem <user> item=amount", aliases=["giveitem"])
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def transferitem(self, ctx, user: discord.User, *, args: str):
        args = args.split("=")
        if len(args) == 1:
            args.append(1)
        elif len(args) != 2:
            await ctx.send(f"{ctx.author.mention} Wenn du mehrere Items auf einmal vergeben möchtest, benutze `{ctx.prefix}transferitem item=3`")
            return
        arg = args[0]
        amount = int(args[1])
        item = self.con["items"].find_one({"_id": arg})
        if not item:
            item = self.con["tools"].find_one({"_id": arg})
        if item:
            count = self.con["inventory"].find_one(
                {"_id": ctx.author.id, item["_id"]: {"$gt": amount - 1}})
            if not count:
                await ctx.send(embed=discord.Embed(
                    color=discord.Color.red(),
                    title="Verkaufen nicht möglich",
                    description=f"Du hast nicht genügend Items"
                ))
            else:
                remove_item(ctx.author, item["_id"], amount)
                self.con["inventory"].update({"_id": user.id}, {"$inc": {item["_id"]: amount}}, upsert=True)
                await ctx.send(f"{user.mention} Du hast {amount}x {item['_id'].title()} {item['emoji']} von **{ctx.author}** bekommen")
        else:
            await ctx.send(f"{user.mention} Ich konnte dieses Item nicht finden.")


def setup(bot):
    bot.add_cog(Economy(bot))
