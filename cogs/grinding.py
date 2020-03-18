import discord
from discord.ext import commands
from main import con
from utils.checks import commands_only, has_pet
from utils.utils import convert_pet, lvlcalc, get_tool_rarity, get_random_drops, get_repair_item
from cogs.economy import remove_item
import datetime
import random
import json
import asyncio


class Grinding(commands.Cog, command_attrs=dict(cooldown_after_parsing=True)):

    def __init__(self, bot):
        self.emoji = ":pick:"
        self.bot = bot
        with open("data/crafting.json", "r", encoding="UTF-8") as f:
            self.recipes = json.load(f)

    @commands.command(usage="craft <item>", aliases=["crafting"])
    @commands_only()
    async def craft(self, ctx, *, args: str = None):
        """Carfting-Commands"""
        inv = con["inventory"].find_one({"_id": ctx.author.id})
        items = list(con["items"].find())
        tools = list(con["tools"].find())
        emojis = {item["_id"]: item["emoji"] for item in items + tools}
        tools = [t["_id"] for t in tools]
        if not args:
            page = 0
            pages = len(self.recipes)

            def create_embed(p):
                element = list(self.recipes)[p]
                new_embed = discord.Embed(
                    color=discord.Color.blue(),
                    title=f"{element.title()} ({p + 1}/{pages})",
                    description=f"Benutze `{ctx.prefix}craft item`, um ein Item zu craften.\nWenn du mehrere Items auf einmal craften möchtest, benutze `{ctx.prefix}craft item=3`\n"
                )
                for crafting_item, ingredients in [(a, b) for a, b in self.recipes[element].items()]:
                    copy = [k for k in ingredients.keys()]
                    for i in copy:
                        if i in tools:
                            ingredients.pop(i)
                    crafting_recipe = ''
                    ing = []
                    for i, c in ingredients.items():
                        ing.append(f"{c}x {emojis[i]}")
                    crafting_recipe += "\n> " + " ".join(ing)
                    new_embed.description += f"\n**» {emojis[crafting_item]} __{crafting_item.title()}__**:{crafting_recipe}"
                return new_embed

            menu = await ctx.send(embed=create_embed(page))
            if pages > 1:
                reactions = ['◀', '▶']
                for reaction in reactions:
                    await menu.add_reaction(reaction)
                while True:
                    try:
                        reaction, user = await ctx.bot.wait_for("reaction_add",
                                                                check=lambda r, u: r.message.id == menu.id and u == ctx.author and str(r.emoji) in reactions,
                                                                timeout=60)
                    except asyncio.TimeoutError:
                        await menu.clear_reactions()
                        return
                    await menu.remove_reaction(reaction, user)
                    if str(reaction.emoji) == reactions[0] and page > 0:
                        page -= 1
                    elif str(reaction.emoji) == reactions[1] and page < pages - 1:
                        page += 1
                    await menu.edit(embed=create_embed(page))
        else:
            recipes = {}
            for group in self.recipes.values():
                for name, recipe in group.items():
                    recipes[name] = recipe
            args = args.split("=")
            if len(args) == 1:
                args.append(1)
            elif len(args) != 2:
                await ctx.send(
                    f"{ctx.author.mention} Wenn du mehrere Items auf einmal craften möchtest, benutze `{ctx.prefix}craft item=3`")
                return
            item = args[0]
            amount = int(args[1])
            if item.lower() in recipes:
                recipe = recipes[item.lower()]
                embed = discord.Embed(
                    color=discord.Color.green(),
                    title=item.title(),
                    description=""
                )
                missing = False
                inc = {}
                unset = {}
                for ingredient, count in recipe.items():
                    count = count * amount
                    inv_count = inv.get(ingredient, 0)
                    if inv_count > count:
                        inv_count = count
                        inc[ingredient] = -count
                    elif count == inv_count:
                        unset[ingredient] = 1
                    else:
                        missing = True
                    embed.description += f"\n> **{inv_count}/{count}** {ingredient.title()} {emojis[ingredient]}"
                if missing:
                    embed.color = discord.Color.red()
                    await ctx.send(embed=embed)
                else:
                    msg = await ctx.send(embed=embed)
                    await msg.add_reaction("☑️")
                    try:
                        _, _ = await ctx.bot.wait_for("reaction_add",
                                                      check=lambda r, u: r.message.id == msg.id and u == ctx.author and str(r.emoji) == "☑️",
                                                      timeout=60)
                    except asyncio.TimeoutError:
                        await msg.clear_reactions()
                        return
                    if item.lower() in tools:
                        con["inv_tools"].update({"_id": ctx.author.id}, {"$inc": {item.lower(): 1}}, upsert=True)
                    else:
                        inc[item.lower()] = amount
                    if unset:
                        con["inventory"].update({"_id": ctx.author.id}, {"$inc": inc, "$unset": unset}, upsert=True)
                    else:
                        con["inventory"].update({"_id": ctx.author.id}, {"$inc": inc}, upsert=True)
                    await msg.clear_reactions()
                    await msg.edit(embed=discord.Embed(
                        color=discord.Color.green(),
                        title="Crafting erfolgreich!",
                        description=f"{ctx.author.mention} Du hast {amount}x **{item.title()}** {emojis[item.lower()]} gecraftet!"
                    ))
            else:
                await ctx.send(f"{ctx.author.mention} Ich konnte dieses Item nicht finden.")

    @commands.command()
    @commands.cooldown(1, 3, commands.BucketType.user)
    @commands_only()
    async def repair(self, ctx, *, tool: str):
        """Repariert ein Werkzeug und füllt die HP wieder auf"""
        tool = tool.lower()
        inv = con["inv_tools"].find_one({"_id": ctx.author.id, tool: {"$exists": True}})
        if inv:
            rarity = get_tool_rarity(tool)
            item = get_repair_item(rarity)
            item = con["items"].find_one({"_id": item})
            check = con["inventory"].find_one({"_id": ctx.author.id, item["_id"]: {"$gt": 0}})
            if check:
                cap = inv[tool]["max"]
                if inv[tool]["dur"] == cap:
                    await ctx.send(embed=discord.Embed(
                        color=discord.Color.orange(),
                        title="Dieses Tool ist schon repariert",
                        description=f"{ctx.author.mention} Du kannst dieses Tool nicht reparieren"
                    ))
                else:
                    con["inv_tools"].update({"_id": ctx.author.id}, {"$set": {f"{tool}.dur": cap}})
                    remove_item(ctx.author, item["_id"], 1)
                    await ctx.send(embed=discord.Embed(
                        color=discord.Color.green(),
                        title="Reparatur erfolgreich",
                        description=f"{ctx.author.mention} Du hast **{tool.title()}** repariert (`{inv[tool]['dur']}` -> `{cap}`)"
                    ))
            else:
                await ctx.send(embed=discord.Embed(
                    color=discord.Color.red(),
                    title="Du hast nicht die nötigen Materialien",
                    description=f"{ctx.author.mention} Du brauchst mindestens **1x {item['emoji']} {item['_id'].title()}**"
                ))
        else:
            await ctx.send(embed=discord.Embed(
                color=discord.Color.red(),
                title="Tool nicht gefunden",
                description=f"{ctx.author.mention} Bitte überprüfe den Namen oder stelle sicher, dass du dieses Tool besitzt"
            ))
            return

    @commands.command()
    @commands.cooldown(1, 300, commands.BucketType.user)
    @commands_only()
    async def mine(self, ctx, *, pick: str = None):
        """Baue Resourcen ab und bekomme Items"""
        pickaxes = ["infinity spitzhacke", "neutron spitzhacke", "komet spitzhacke", "stern spitzhacke",
                    "pauls spitzhacke"]
        if pick:
            inv = con["inv_tools"].find_one({"_id": ctx.author.id, pick: {"$exists": True}})
            if not inv or pick not in pickaxes:
                await ctx.send(embed=discord.Embed(
                    color=discord.Color.red(),
                    title="Spitzhacke nicht gefunden",
                    description=f"{ctx.author.mention} Bitte überprüfe den Namen und stelle sicher, dass du diese Spitzhacke besitzt"
                ))
                ctx.command.reset_cooldown(ctx)
                return
            pickaxe = inv[pick]
        else:
            inv = con["inv_tools"].find_one(
                {"_id": ctx.author.id, "$or": [{pick: {"$exists": True}} for pick in pickaxes]})
            if not inv:
                await ctx.send(embed=discord.Embed(
                    color=discord.Color.red(),
                    title="Du besitzt keine Spitzhacke",
                    description=f"{ctx.author.mention} Du brauchst eine Spitzhacke, um diesen Command verwenden zu können. Siehe `{ctx.prefix}shop` & `{ctx.prefix}craft`"
                ))
                ctx.command.reset_cooldown(ctx)
                return
            for pick in pickaxes:
                pickaxe = inv.get(pick, None)
                if pickaxe:
                    break
        dur = pickaxe["dur"]
        tool = con["tools"].find_one({"_id": pick})
        emojis = {item["_id"]: item["emoji"] for item in list(con["items"].find())}
        rarity = get_tool_rarity(tool["_id"])
        amount = random.randint(2, 4)
        loot = get_random_drops(rarity, amount)
        embed = discord.Embed(
            color=discord.Color.green(),
            title=f"{tool['emoji']} Du hast ein paar Items abgebaut!",
            description=""
        )
        if dur == 1:
            embed.description = f"Oh Nein! Deine Spitzhacke ist kaputt gegangen. Pass das nächste mal besser auf."
            if len(inv) > 2:
                con["inv_tools"].update({"_id": ctx.author.id}, {"$unset": {tool['_id']: 1}})
            else:
                con["inv_tools"].delete_one({"_id": ctx.author.id})
        else:
            con["inv_tools"].update({"_id": ctx.author.id}, {"$inc": {f"{tool['_id']}.dur": -1}})
        for item, count in loot.items():
            embed.description += f"\n> **{count}x {item.title()}** {emojis[item]}"
        con["inventory"].update({"_id": ctx.author.id}, {"$inc": loot}, upsert=True)
        embed.set_footer(text=f"mit {tool['_id'].title()}")
        embed.timestamp = datetime.datetime.utcnow()
        await ctx.send(embed=embed)

    @commands.command()
    @commands.cooldown(1, 300, commands.BucketType.user)
    @commands_only()
    async def fish(self, ctx, *, rod: str = None):
        """Angel nach Resourcen und bekomme Items"""
        fishing_rods = ["infinity angel", "neutron angel", "komet angel", "stern angel", "zanas angel"]
        if rod:
            inv = con["inv_tools"].find_one({"_id": ctx.author.id, rod: {"$exists": True}})
            if not inv or rod not in fishing_rods:
                await ctx.send(embed=discord.Embed(
                    color=discord.Color.red(),
                    title="Angel nicht gefunden",
                    description=f"{ctx.author.mention} Bitte überprüfe den Namen und stelle sicher, dass du diese Angel besitzt"
                ))
                ctx.command.reset_cooldown(ctx)
                return
            fishing_rod = inv[rod]
        else:
            inv = con["inv_tools"].find_one(
                {"_id": ctx.author.id, "$or": [{rod: {"$exists": 1}} for rod in fishing_rods]})
            if not inv:
                await ctx.send(embed=discord.Embed(
                    color=discord.Color.red(),
                    title="Du besitzt keine Angel",
                    description=f"{ctx.author.mention} Du brauchst eine Angel, um diesen Command verwenden zu können. Siehe `{ctx.prefix}shop` & `{ctx.prefix}craft`"
                ))
                ctx.command.reset_cooldown(ctx)
                return
            for rod in fishing_rods:
                fishing_rod = inv.get(rod, None)
                if fishing_rod:
                    break
        dur = fishing_rod["dur"]
        tool = con["tools"].find_one({"_id": rod})
        emojis = {item["_id"]: item["emoji"] for item in list(con["items"].find())}
        rarity = get_tool_rarity(tool["_id"])
        amount = random.randint(2, 4)
        loot = get_random_drops(rarity, amount)
        embed = discord.Embed(
            color=discord.Color.green(),
            title=f"{tool['emoji']} Du hast ein paar Items geangelt!",
            description=""
        )
        if dur == 1:
            embed.description = f"Oh Nein! Deine Angel ist kaputt gegangen. Pass das nächste mal besser auf."
            if len(inv) > 2:
                con["inv_tools"].update({"_id": ctx.author.id}, {"$unset": {tool['_id']: 1}})
            else:
                con["inv_tools"].delete_one({"_id": ctx.author.id})
        else:
            con["inv_tools"].update({"_id": ctx.author.id}, {"$inc": {f"{tool['_id']}.dur": -1}})
        for item, count in loot.items():
            embed.description += f"\n> **{count}x {item.title()}** {emojis[item]}"
        con["inventory"].update({"_id": ctx.author.id}, {"$inc": loot}, upsert=True)
        embed.set_footer(text=f"mit {tool['_id'].title()}")
        embed.timestamp = datetime.datetime.utcnow()
        await ctx.send(embed=embed)

    @commands.group(case_insensitive=True)
    @commands_only()
    @has_pet()
    async def pet(self, ctx):
        """Zeigt dir Informationen über dein Pet"""
        if ctx.invoked_subcommand is None:
            pet = con["pets"].find_one({"_id": ctx.author.id})
            stats = convert_pet(pet)
            embed = discord.Embed(
                color=discord.Color.greyple(),
                title=pet["name"],
                description=f"Nutze `{ctx.prefix}help pet` für mehr Info"
            )
            embed.set_thumbnail(url=pet["url"])
            for stat, val in stats.items():
                bar = "▰" * int(val / 10) + "▱" * (10 - int(val / 10))
                embed.add_field(name=stat.title() + f" ({val}%)", value=bar, inline=False)
            level, xp, cap = lvlcalc(pet["xp"])
            per = xp / cap * 10
            string = "▰" * int(per) + "▱" * (10 - int(per))
            bar = f"[{string}](https://www.youtube.com/watch?v=DyDfgMOUjCI&list=RD2G1Bnwsw7lA&index=10)\n`Level {level + 1}`"
            embed.add_field(name=f"Erfahrung ({xp}/{cap})", value=bar)
            await ctx.send(embed=embed)

    @pet.command(usage="name <name>")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def name(self, ctx, *, name: str):
        """Benennt dein Pet um"""
        if len(name) > 25:
            await ctx.send(f"{ctx.author.mention} Der Name darf nicht länger als 25 Zeichen sein.")
        else:
            con["pets"].update({"_id": ctx.author.id}, {"$set": {"name": name}})
            await ctx.send(f"{ctx.author.mention} Der Name wurde in **{name}** geändert.")

    @pet.command(usage="name <avatar>")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def avatar(self, ctx, url: str):
        """Ändert das Bild deines Pets"""
        embed = discord.Embed(
            color=discord.Color.green(),
            title="Avatar wurde geändert"
        )
        embed.set_thumbnail(url=url)
        try:
            await ctx.send(embed=embed)
            con["pets"].update({"_id": ctx.author.id}, {"$set": {"url": url}})
        except discord.HTTPException:
            await ctx.send(f"{ctx.author.mention} Bitte gib eine gültige URL an.")

    @pet.command()
    async def feed(self, ctx):
        """Füttert dein Pet"""
        result = await pet_action(ctx, "hunger")
        if result:
            await ctx.send(f"{ctx.author.mention} Du hast dein Pet für **{result}** Dollar gefüttert.")
        else:
            await ctx.send(f"{ctx.author.mention} Bitte warte noch, bevor du dein Pet füttern kannst.")

    @pet.command()
    async def wash(self, ctx):
        """Wäscht dein Pet"""
        result = await pet_action(ctx, "hygiene")
        if result:
            await ctx.send(f"{ctx.author.mention} Du hast dein Pet für **{result}** Dollar gewaschen.")
        else:
            await ctx.send(f"{ctx.author.mention} Bitte warte noch, bevor du dein Pet waschen kannst.")

    @pet.command()
    async def play(self, ctx):
        """Spiele mit deinem Pet"""
        result = await pet_action(ctx, "fun", cost=False)
        if result:
            await ctx.send(f"{ctx.author.mention} Du hast mit deinem Pet gespielt. **+{result} XP**")
        else:
            await ctx.send(f"{ctx.author.mention} Bitte warte noch, bevor du mit deinem Pet spielen kannst.")

    @pet.command()
    async def train(self, ctx):
        """Trainiere dein Pet"""
        result = await pet_action(ctx, "energy", cost=False)
        if result:
            await ctx.send(f"{ctx.author.mention} Du hast dein Pet trainiert. **+{result} XP**")
        else:
            await ctx.send(f"{ctx.author.mention} Bitte warte noch, bevor du dein Pet trainieren kannst.")


async def pet_action(ctx, action, cost: bool = True):
    pet = con["pets"].find_one({"_id": ctx.author.id})
    stats = convert_pet(pet)
    if cost:
        bal = con["stats"].find_one({"_id": ctx.author.id}, {"balance": 1})["balance"]
        if bal < 50:
            raise commands.CommandError(f"{ctx.author.mention} Du brauchst mindestens **50** Dollar.")
    if stats[action] > 80:
        return False
    else:
        dif = 100 - (stats[action] + random.randint(25, 35))
        if dif < 0:
            dif = 0
        t = datetime.datetime.utcnow() - datetime.timedelta(seconds=120 * dif)
        xp = random.randint(15, 25)
        con["pets"].update({"_id": ctx.author.id}, {"$set": {action: t}, "$inc": {"xp": xp}})
        if cost:
            cost = random.randint(35, 50)
            con["stats"].update({"_id": ctx.author.id}, {"$inc": {"balance": -cost}})
            return cost
        else:
            return xp


def setup(bot):
    bot.add_cog(Grinding(bot))
