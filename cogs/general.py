import discord
from discord.ext import commands
from main import connection
from utils.utils import convert_upgrade_levels
from utils.checks import commands_or_casino_only
from main import lvlcalc
import datetime
import json
import random


class General(commands.Cog, command_attrs=dict(cooldown_after_parsing=True)):
    def __init__(self, bot):
        self.bot = bot
        self.con = connection
        with open("data/config.json", "r") as f:
            self.config = json.load(f)
        self.booster_role_position = self.config["booster_role_position"]

    @commands.command(usage='afk <message>')
    @commands.cooldown(1, 10, commands.BucketType.member)
    async def afk(self, ctx, message: str = "Keinen Grund angegeben"):
        """Setzt eine Afk-Nachricht, die andere sehen werden, wenn sie dich pingen"""
        self.con["afk"].update({"_id": ctx.author.id}, {
            "message": message,
            "time": datetime.datetime.utcnow()
        }, upsert=True)
        await ctx.send(embed=discord.Embed(
            color=discord.Color.green(),
            title='Auf Wiedersehen!',
            description='Deine AFK-Nachricht wurde gesetzt'
        ))

    @commands.command(usage="limit <limit>", aliases=["setlimit", "vclimit"])
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def limit(self, ctx, limit: int):
        """Ändert das Limit deines privaten Voicechannels"""
        if ctx.author.voice is None:
            await ctx.send(embed=discord.Embed(
                color=discord.Color.red(),
                title=':no_entry: Du bist in keinem privaten Channel',
                description='Joine `「＋」VC Erstellen`, um einen neuen Channel zu erstellen'
            ))
        elif ctx.author.voice.channel.category_id != self.config["avc_category"] and ctx.author.voice.channel.id != \
                self.config["avc_channel"]:
            await ctx.send(embed=discord.Embed(
                color=discord.Color.red(),
                title=':no_entry: Nicht möglich',
                description='Du kannst diesen Channel nicht bearbeiten'
            ))
        else:
            await ctx.author.voice.channel.edit(user_limit=limit)
            await ctx.send(f"{ctx.author.mention} Das Limit wurde auf `{limit}` gesetzt")

    @commands.command(usage="name <name>", aliases=["setname", "vcname"])
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def name(self, ctx, *, name: str):
        """Ändert den Namen deines Voicechannels"""
        if ctx.author.voice is None:
            await ctx.send(embed=discord.Embed(
                color=discord.Color.red(),
                title=':no_entry: Du bist in keinem privaten Channel',
                description='Joine `「＋」VC Erstellen`, um einen neuen Channel zu erstellen'
            ))
        elif ctx.author.voice.channel.category_id != self.config["avc_category"] and ctx.author.voice.channel.id != \
                self.config["avc_channel"]:
            await ctx.send(embed=discord.Embed(
                color=discord.Color.red(),
                title=':no_entry: Nicht möglich',
                description='Du kannst diesen Channel nicht bearbeiten'
            ))
        else:
            await ctx.author.voice.channel.edit(name=name)
            await ctx.send(f"{ctx.author.mention} Der Name wurde in **{name}** geändert")

    @commands.group(usage='customrole [create|delete|name|color|random]', aliases=["crole"], case_insensitive=True)
    @commands.has_role('Nitro Booster')
    async def customrole(self, ctx: commands.Context):
        """Commands für eine eigene Rolle"""
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    @customrole.command(usage='create [color] [name]', aliases=['add', 'new'])
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def create(self, ctx, color: discord.Color, *, name: str):
        """Erstellt dir eine eigene Rolle"""
        check = self.con["booster"].find_one({"_id": ctx.author.id})
        if check:
            await ctx.send(f"{ctx.author.mention} Du besitzt bereits eine Rolle")
        else:
            role = await ctx.guild.create_role(color=color, name=name)
            await ctx.author.add_roles(role)
            await role.edit(position=len(ctx.guild.roles) - self.booster_role_position)
            self.con["booster"].insert_one({"_id": ctx.author.id, "role": role.id})
            await ctx.send(embed=discord.Embed(
                color=color,
                title=name,
                description=f'Die Rolle wurde erfolgreich erstellt'
            ))

    @customrole.command(aliases=['remove'])
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def delete(self, ctx):
        """Löscht deine aktuelle Rolle"""
        role = self.con["booster"].find_one({"_id": ctx.author.id})
        if not role:
            await ctx.send(f"{ctx.author.mention} Du besitzt keine Rolle")
        else:
            self.con["booster"].delete_one({"_id": ctx.author.id})
            role = ctx.guild.get_role(role["role"])
            await role.delete()
            await ctx.send(f"{ctx.author.mention} Deine Rolle wurde erfolgreich gelöscht")

    @customrole.command(aliases=['colour', 'farbe'])
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def color(self, ctx, color: discord.Color):
        """Ändert die Farbe deiner Rolle"""
        role = self.con["booster"].find_one({"_id": ctx.author.id})
        if not role:
            await ctx.send(f"{ctx.author.mention} Du besitzt keine Rolle")
        else:
            role = ctx.guild.get_role(role["role"])
            await role.edit(color=color)
            await ctx.send(embed=discord.Embed(
                color=color,
                title=str(color),
                description=f"Deine Farbe wurde erfolgreich geändert"
            ))

    @customrole.command()
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def name(self, ctx, *, name: str):
        """Ändert den Namen deiner Rolle"""
        role = self.con["booster"].find_one({"_id": ctx.author.id})
        if not role:
            await ctx.send(f"{ctx.author.mention} Du besitzt keine Rolle")
        else:
            role = ctx.guild.get_role(role["role"])
            await role.edit(name=name)
            await ctx.send(embed=discord.Embed(
                color=role.color,
                title=name,
                description="Der Name deiner Rolle wurde erfolgreich geändert"
            ))

    @customrole.command()
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def random(self, ctx):
        """Gibt deiner Rolle eine zufällige Farbe"""
        role = self.con["booster"].find_one({"_id": ctx.author.id})
        if not role:
            await ctx.send(f"{ctx.author.mention} Du besitzt keine Rolle")
        else:
            color = discord.Color(random.randint(0, 0xffffff))
            role = ctx.guild.get_role(role["role"])
            await role.edit(color=color)
            await ctx.send(embed=discord.Embed(
                color=color,
                title=str(color),
                description="Deine Farbe wurde geändert"
            ))

    @commands.group(usage='upgrade <item>', aliases=['u', 'upgrade', 'tier'], case_insensitive=True)
    #@commands_or_casino_only()
    async def upgrades(self, ctx, upgrade: str = None, amount: str = "1"):
        """Zeigt deine Upgrades"""
        stats = self.con["stats"].find_one({"_id": ctx.author.id})
        level, _, _ = lvlcalc(stats["total_xp"])
        u = self.con["upgrades"].find_one({"_id": ctx.author.id})
        stat_points = level-(u['multiplier'] + u['money'] + u['crit'])
        if upgrade is None:
            embed = discord.Embed(
                color=discord.Color.blurple(),
                title=f"Upgrades von {ctx.author}",
                description=f"Benutze `{ctx.prefix}upgrade`, um etwas upzugraden\n\n**Übrige Stat-Points: {stat_points}**"
            )
            mult, money, crit = convert_upgrade_levels(u["multiplier"], u["money"], u["crit"])

            def create_bar(lvl):
                bar = "▰" * lvl + "▱" * (10-lvl)
                string = f"[{bar}](https://www.youtube.com/watch?v=DyDfgMOUjCI&list=RD2G1Bnwsw7lA&index=10)"
                return string

            embed.add_field(
                name=f":sparkles: XP pro Nachricht: {mult}%",
                value=f"**{create_bar(u['multiplier'])} ({u['multiplier']}/10)**\n*Erhöht die XP, die du pro Nachricht bekommst (2m)*\n`{ctx.prefix}upgrade multiplier`", inline=False)
            embed.add_field(
                name=f":money_with_wings: Dollar pro Nachricht: {money}",
                value=f"**{create_bar(u['money'])} ({u['money']}/10)**\n*Erhöht das Geld, das du pro Nachricht bekommst (2m)*\n`{ctx.prefix}upgrade money`", inline=False)
            embed.add_field(
                name=f":four_leaf_clover: Crit Chance: {crit}%",
                value=f"**{create_bar(u['crit'])} ({u['crit']}/10)**\n*Erhöht die Chance, dass du doppelt XP & Geld bekommst*\n`{ctx.prefix}upgrade crit`", inline=False)
            await ctx.send(embed=embed)
        elif upgrade.lower() in ["multiplier", "money", "crit"]:
            if stat_points > 0:
                if amount.isdigit():
                    amount = int(amount)
                elif amount.lower() in ["max", "all"]:
                    amount = 10 - u[upgrade.lower()]
                else:
                    await ctx.send(f"{ctx.author.mention} Bitte gib eine Zahl oder max an. Z.b. `{ctx.prefix}upgrade crit max`")
                    return
                if u[upgrade.lower()] + amount <= 10:
                    self.con["upgrades"].update({"_id": ctx.author.id}, {"$inc": {upgrade.lower(): 1}})
                    await ctx.send(f"{ctx.author.mention} Du hast **{upgrade.title()}** auf Level **{u[upgrade.lower()]+1}** erweitert")
                elif u[upgrade.lower()] == 10:
                    await ctx.send(f"{ctx.author.mention} Du hast bereits das Maximallevel von **{upgrade.title()}** erreicht.")
                else:
                    await ctx.send(f"{ctx.author.mention} Du kannst dieses Level nicht um **{amount}** erhöhen.")
            else:
                await ctx.send(f"{ctx.author.mention} Du hast nicht genügend Stat-Points. Du bekommst mehr, wenn du auflevelst.")
        else:
            await ctx.send(f"{ctx.author.mention} Ich konnte dieses Upgrade nicht finden.")

    @commands.group(usage='todo [add|remove|clear]', case_insensitive=True)
    async def todo(self, ctx):
        """Deine Todo-Liste"""
        if ctx.invoked_subcommand is None:
            todo = self.con["todo"].find_one({"_id": ctx.author.id})
            if todo:
                msg = f"**__Todo von {ctx.author}__:**  "
                for i, entry in enumerate(todo["todo"], 1):
                    msg += f"\n**{i}.** {entry}"
                await ctx.send(msg)
            else:
                await ctx.send(f"{ctx.author.mention} Du hast derzeit nichts zu tun")

    @todo.command(usage="add <Eintrag>")
    async def add(self, ctx, *, entry: str):
        """Fügt einen neuen Stichpunkt zu deiner Todo-Liste hinzu"""
        self.con["todo"].update({"_id": ctx.author.id}, {"$push": {"todo": entry}}, upsert=True)
        await ctx.send(f"{ctx.author.mention} Neuer Stichpunkt wurde hinzugefügt.\n```{entry}```")

    @todo.command(usage="edit <Nummer> <Eintrag>")
    async def edit(self, ctx, number: int, *, entry: str):
        """Ändert einen Punkt in deiner Todo-Liste"""
        todo = self.con["todo"].find_one({"_id": ctx.author.id})
        if todo:
            todo = todo["todo"]
            if 1 <= number <= len(todo):
                todo[number - 1] = entry
                self.con["todo"].update({"_id": ctx.author.id}, {"$set": {"todo": todo}}, upsert=True)
                await ctx.send(f"{ctx.author.mention} Stichpunkt wurde geändert.\n```{entry}```")
            else:
                await ctx.send(f"{ctx.author.mention} Stichpunkt nicht gefunden!")
        else:
            await ctx.send(f"{ctx.author.mention} Du hast keine Todo-Liste!")

    @todo.command(usage="remove <Nummer>", aliases=["del"])
    async def remove(self, ctx, *, number: int):
        """Entfernt einen Stichpunkt aus deiner Todo-Liste"""
        todo = self.con["todo"].find_one({"_id": ctx.author.id})
        if todo:
            todo = todo["todo"]
            if 1 <= number <= len(todo):
                if len(todo) == 1:
                    self.con["todo"].delete_one({"_id": ctx.author.id})
                else:
                    todo.pop(number - 1)
                    self.con["todo"].update({"_id": ctx.author.id}, {"$set": {"todo": todo}})
                await ctx.send(f"{ctx.author.mention} Stichpunkt wurde gelöscht.")
            else:
                await ctx.send(f"{ctx.author.mention} Stichpunkt nicht gefunden!")
        else:
            await ctx.send(f"{ctx.author.mention} Du hast keine Todo-Liste!")

    @todo.command(aliases=["clean"])
    async def clear(self, ctx):
        """Entfernt alle Stichpunkte aus deiner Todo-Liste"""
        todo = self.con["todo"].find_one({"_id": ctx.author.id})
        if todo:
            self.con["todo"].delete_one({"_id": ctx.author.id})
            await ctx.send(f"{ctx.author.mention} {len(todo)} Stichpunkte wurden gelöscht.")
        else:
            await ctx.send(f"{ctx.author.mention} Du hast keine Todo-Liste!")

    @commands.command(usage="iteminfo <item>")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def iteminfo(self, ctx, *, item: str):
        """Zeigt dir Informationen über ein Item"""
        async with ctx.typing():
            item = item.lower()
            result1 = self.con["items"].find_one({"_id": item})
            result2 = self.con["tools"].find_one({"_id": item})
            result3 = self.con["mine-drops"].find_one({"_id": item})
            result4 = self.con["fish-drops"].find_one({"_id": item})
            items = list(self.con["items"].find())
            emojis = {item["_id"]: item["emoji"] for item in items}
            embed = discord.Embed(
                color=discord.Color.blurple(),
                title=f"__Infos über {item.title()}__"
            )
            if not result1 and not result2:
                await ctx.send(f"{ctx.author.mention} Ich konnte dieses Item nicht finden.")
                return
            if result1:
                result = result1
                description = f"\n**Einkaufspreis**: {result['buy']} Dollar"
            else:
                result = result2
                description = ""
                if result3 or result4:
                    item = result3 or result4
                    description += f"\n**Bruch-Wahrscheinlichkeit**: {item['break'] * 100}%\n**Geld-Drops**: {item['cash']} Dollar\n**Item-Drops**: {item['items']} Items\n\n:bar_chart: **Item-Drop-Wahrscheinlichkeiten**:"
                    for drop, prop in reversed(list(item["props"].items())):
                        description += f"\n> {emojis[drop]} **{drop}** - {int(prop*100)}%"
            embed.description = f"**Beschreibung**: {result['description']}\n**Emoji**: {result['emoji']}\n**Verkaufspreis**: {result['sell']} Dollar" + description
            await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(General(bot))
