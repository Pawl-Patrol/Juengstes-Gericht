import discord
from discord.ext import commands
from main import connection
from utils.upgrades import get_upgrade_price, convert_upgrade_levels
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
        self.con["afk"].update({
            "_id": ctx.author.id,
            "message": message,
            "time": str(datetime.datetime.now())
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
    @commands_or_casino_only()
    async def upgrades(self, ctx: commands.Context):
        """Zeigt deine Upgrades"""
        if ctx.invoked_subcommand is None:
            u = self.con["upgrades"].find_one({"_id": ctx.author.id})
            embed = discord.Embed(
                color=discord.Color.blurple(),
                title=f"Upgrades von {ctx.author}",
                description=f"Benutze `{ctx.prefix}upgrade`, um etwas upzugraden"
            )
            mult_lvl, money_lvl, income_lvl, crit_lvl, power_lvl = u['multiplier'], u['money'], u['income'], u['crit'], \
                                                                   u['power']
            mult_value, money_value, income_value, crit_value, power_value = convert_upgrade_levels(mult_lvl, money_lvl,
                                                                                                    income_lvl,
                                                                                                    crit_lvl, power_lvl)
            mult_price = get_upgrade_price(mult_lvl=mult_lvl + 1)
            money_price = get_upgrade_price(money_lvl=money_lvl + 1)
            income_price = get_upgrade_price(income_lvl=income_lvl + 1)
            crit_price = get_upgrade_price(crit_lvl=crit_lvl + 1)
            power_price = get_upgrade_price(power_lvl=power_lvl + 1)
            embed.add_field(
                name=f":sparkles: XP-Boost | {mult_price} :dollar: | Level {mult_lvl} ({mult_value}% Multiplier)",
                value=f"Erhöht deine XP pro Nachricht.\n`ok upgrade xp`", inline=False)
            embed.add_field(
                name=f":money_with_wings: Dollar pro Nachricht | {money_price} :dollar: | Level {money_lvl} ({money_value} Dollar)",
                value=f"Erhöht die Anzahl an Dollar pro Nachricht\n`ok upgrade money`", inline=False)
            embed.add_field(
                name=f":moneybag: Einkommen | {income_price} :dollar: | Level {income_lvl} ({income_value} Dollar)",
                value=f"Erhöht die Anzahl an Dollar, die du pro 10 Minuten bekommst\n`ok upgrade income`", inline=False)
            embed.add_field(
                name=f":four_leaf_clover: Kritische Treffer | {crit_price} :dollar: | Level {crit_lvl} ({crit_value}% Chance)",
                value=f"Erhöht die Wahrscheilichkeit, dass du doppelt so viel Geld und XP für eine Nachricht bekommst\n`ok upgrade crit`",
                inline=False)
            embed.add_field(
                name=f":thunder_cloud_rain: Geldregen | {power_price} :dollar: | Level {power_lvl} ({power_value} Dollar)",
                value=f"Erhöht die Anzahl an Dollar, die du bei einem Geldregen bekommst (1%)\n`ok upgrade power`",
                inline=False)
            await ctx.send(embed=embed)

    @upgrades.command()
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def xp(self, ctx, amount: int = 1):
        """Erhöht deine XP pro Nachricht"""
        stats = self.con["stats"].find_one({"_id": ctx.author.id})
        user_lvl, _, _ = lvlcalc(stats["total_xp"])
        u = self.con["upgrades"].find_one({"_id": ctx.author.id})
        level = u["multiplier"] + amount
        price = get_upgrade_price(mult_lvl=level)
        if stats["balance"] < price:
            await ctx.send(
                f"{ctx.author.mention} Du brauchst mindestens **{price}** Dollar, um dieses Upgrade zu kaufen")
        elif level > 50:
            await ctx.send(f"{ctx.author.mention} Du kannst nicht höher als Level 50 upgraden")
        # elif user_lvl < level:
        else:
            self.con["stats"].update({"_id": ctx.author.id}, {"$inc": {"balance": -price}})
            self.con["upgrades"].update({"_id": ctx.author.id}, {"$inc": {"multiplier": amount}})
            await ctx.send(f"{ctx.author.mention} Du hast deinen XP-Multiplier auf **Level {level}** erweitert")

    @upgrades.command()
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def money(self, ctx, amount: int = 1):
        """Erhöht die Anzahl an Dollar pro Nachricht"""
        bal = self.con["stats"].find_one({"_id": ctx.author.id}, {"balance": 1})["balance"]
        u = self.con["upgrades"].find_one({"_id": ctx.author.id})
        level = u["money"] + amount
        price = get_upgrade_price(money_lvl=level)
        if bal < price:
            await ctx.send(
                f"{ctx.author.mention} Du brauchst mindestens **{price}** Dollar, um dieses Upgrade zu kaufen")
        elif level > 50:
            await ctx.send(f"{ctx.author.mention} Du kannst nicht höher als Level 50 upgraden")
        else:
            self.con["stats"].update({"_id": ctx.author.id}, {"$inc": {"balance": -price}})
            self.con["upgrades"].update({"_id": ctx.author.id}, {"$inc": {"money": amount}})
            await ctx.send(f"{ctx.author.mention} Du hast deine Dollar pro Nachricht auf **Level {level}** erweitert")

    @upgrades.command()
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def income(self, ctx, amount: int = 1):
        """Erhöht die Anzahl an Dollar, die du pro 10 Minuten bekommst"""
        bal = self.con["stats"].find_one({"_id": ctx.author.id}, {"balance": 1})["balance"]
        u = self.con["upgrades"].find_one({"_id": ctx.author.id})
        level = u["income"] + amount
        price = get_upgrade_price(income_lvl=level)
        if bal < price:
            await ctx.send(
                f"{ctx.author.mention} Du brauchst mindestens **{price}** Dollar, um dieses Upgrade zu kaufen")
        elif level > 50:
            await ctx.send(f"{ctx.author.mention} Du kannst nicht höher als Level 50 upgraden")
        else:
            self.con["stats"].update({"_id": ctx.author.id}, {"$inc": {"balance": -price}})
            self.con["upgrades"].update({"_id": ctx.author.id}, {"$inc": {"income": amount}})
            await ctx.send(f"{ctx.author.mention} Du hast dein Einkommen auf **Level {level}** erweitert")

    @upgrades.command()
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def crit(self, ctx, amount: int = 1):
        """Erhöht die Wahrscheilichkeit, dass du doppelt so viel Geld und XP für eine Nachricht bekommst"""
        bal = self.con["stats"].find_one({"_id": ctx.author.id}, {"balance": 1})["balance"]
        u = self.con["upgrades"].find_one({"_id": ctx.author.id})
        level = u["crit"] + amount
        price = get_upgrade_price(crit_lvl=level)
        if bal < price:
            await ctx.send(
                f"{ctx.author.mention} Du brauchst mindestens **{price}** Dollar, um dieses Upgrade zu kaufen")
        elif level > 50:
            await ctx.send(f"{ctx.author.mention} Du kannst nicht höher als Level 50 upgraden")
        else:
            self.con["stats"].update({"_id": ctx.author.id}, {"$inc": {"balance": -price}})
            self.con["upgrades"].update({"_id": ctx.author.id}, {"$inc": {"crit": amount}})
            await ctx.send(f"{ctx.author.mention} Du hast deine kritischen Treffer auf **Level {level}** erweitert")

    @upgrades.command()
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def power(self, ctx, amount: int = 1):
        """Erhöht die Anzahl an Dollar, die du bei einem Geldregen bekommst (1%)"""
        bal = self.con["stats"].find_one({"_id": ctx.author.id}, {"balance": 1})["balance"]
        u = self.con["upgrades"].find_one({"_id": ctx.author.id})
        level = u["power"] + amount
        price = get_upgrade_price(power_lvl=level)
        if bal < price:
            await ctx.send(
                f"{ctx.author.mention} Du brauchst mindestens **{price}** Dollar, um dieses Upgrade zu kaufen")
        elif level > 50:
            await ctx.send(f"{ctx.author.mention} Du kannst nicht höher als Level 50 upgraden")
        else:
            self.con["stats"].update({"_id": ctx.author.id}, {"$inc": {"balance": -price}})
            self.con["upgrades"].update({"_id": ctx.author.id}, {"$inc": {"power": amount}})
            await ctx.send(f"{ctx.author.mention} Du hast deinen Geldregen auf **Level {level}** erweitert")

    @commands.command(aliases=["prefix"])
    async def setprefix(self, ctx, *, prefix=""):
        """Legt einen Prefix nur für dich fest"""
        with open("data/prefixes.json", "r") as f:
            prefixes = json.load(f)
        if prefix == "":
            if str(ctx.author.id) in prefixes:
                await ctx.send(f"{ctx.author.mention} Dein Prefix ist `{prefixes[str(ctx.author.id)]}`")
            else:
                await ctx.send(f"{ctx.author.mention} Du hast keinen eigenen Prefix.")
        else:
            prefixes[str(ctx.author.id)] = prefix
            with open("data/prefixes.json", "w") as f:
                json.dump(prefixes, f, indent=4)
            await ctx.send(f"{ctx.author.mention} Dein Prefix ist jetzt `{prefix}`.")

    @commands.command()
    async def delprefix(self, ctx):
        """Entfernt deinen persönlichen Prefix"""
        with open("data/prefixes.json", "r") as f:
            prefixes = json.load(f)
        prefixes.pop(str(ctx.author.id))
        with open("data/prefixes.json", "w") as f:
            json.dump(prefixes, f, indent=4)
        await ctx.send(f"{ctx.author.mention} Dein Prefix wurde gelöscht.")

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


def setup(bot):
    bot.add_cog(General(bot))
