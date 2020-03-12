import discord
from discord.ext import commands
from main import connection
from utils.checks import commands_or_casino_only, owner_only
import pymongo
import random


class Currency(commands.Cog, command_attrs=dict(cooldown_after_parsing=True)):

    def __init__(self, bot):
        self.emoji = ":moneybag:"
        self.bot = bot
        self.con = connection

    @commands.command(usage='balance [user]', aliases=['bal', 'bank', 'credits', 'money'])
    @commands.cooldown(1, 3, commands.BucketType.user)
    @commands_or_casino_only()
    async def balance(self, ctx, user: discord.User = None):
        """Zeigt dir dein Geld oder das von einem anderen Nutzer"""
        if not user:
            user = ctx.author
        stats = self.con["stats"].find_one({"_id": user.id}, {"balance": 1, "bank": 1, "max": 1})
        await ctx.send(embed=discord.Embed(
            color=discord.Color.green(),
            title=f'Bilanz von {user.display_name}',
            description=f'**Bargeld:** {stats["balance"]} :dollar:\n**Bank:** {stats["bank"]}/{stats["max"]}'
        ))

    @commands.command(usage='withdraw [amount]', aliases=['with'])
    @commands.cooldown(1, 3, commands.BucketType.user)
    @commands_or_casino_only()
    async def withdraw(self, ctx, amount):
        """Hebt Geld von deiner Bank ab"""
        stats = self.con["stats"].find_one({"_id": ctx.author.id}, {"balance": 1, "bank": 1})
        if amount.isdigit():
            amount = int(amount)
        elif amount in ['max', 'all']:
            amount = stats["bank"]
        else:
            await ctx.send(embed=discord.Embed(
                color=discord.Color.red(),
                title='Wie viel Geld willst du abheben?',
                description='Bitte gib eine **Zahl** "**all**" oder "**max**" an'
            ))
            return
        if amount > stats["bank"]:
            await ctx.send(f"{ctx.author.mention} Du hast nicht genügend Geld auf deiner Bank")
        elif amount < 1:
            await ctx.send(f"{ctx.author.mention} Du musst mindestens 1 :dollar: von deiner Bank abheben")
        else:
            self.con["stats"].update({"_id": ctx.author.id}, {"$inc": {"balance": amount, "bank": -amount}})
            await ctx.send(embed=discord.Embed(
                color=discord.Color.green(),
                title='Transaktion erfolgreich',
                description=f'Du hast **{amount}** :dollar: abgehoben'
            ))

    @commands.command(usage='deposit [amount]', aliases=['dep'])
    @commands.cooldown(1, 3, commands.BucketType.user)
    @commands_or_casino_only()
    async def deposit(self, ctx, amount):
        """Zahlt Geld auf deine Bank ein"""
        stats = self.con["stats"].find_one({"_id": ctx.author.id}, {"balance": 1, "bank": 1, "max": 1})
        if amount.isdigit():
            amount = int(amount)
        elif amount in ['max', 'all']:
            amount = stats["max"] - stats["bank"]
            if amount > stats["balance"]:
                amount = stats["balance"]
        else:
            await ctx.send(embed=discord.Embed(
                color=discord.Color.red(),
                title='Wie viel Geld willst du einzahlen?',
                description='Bitte gib eine **Zahl** "**all**" oder "**max**" an'
            ))
            return
        if amount > stats["balance"]:
            await ctx.send(f"{ctx.author.mention} Du hast nicht genügend Bargeld")
        elif stats["bank"] == stats["max"]:
            await ctx.send(f"{ctx.author.mention} Deine Bank ist schon voll")
        elif amount < 1:
            await ctx.send(f"{ctx.author.mention} Du musst mindestens 1 :dollar: einzahlen")
        else:
            if amount + stats["bank"] > stats["max"]:
                amount = stats["max"] - stats["bank"]
            self.con["stats"].update({"_id": ctx.author.id}, {"$inc": {"balance": -amount, "bank": amount}})
            await ctx.send(embed=discord.Embed(
                color=discord.Color.green(),
                title='Transaktion erfolgreich',
                description=f'Du hast **{amount}** :dollar: eingezahlt'
            ))

    @commands.command()
    @commands.cooldown(1, 3, commands.BucketType.channel)
    @commands_or_casino_only()
    async def rich(self, ctx):
        """Zeigt die 10 reichsten Member"""
        results = self.con["stats"].find({}).sort("balance", pymongo.DESCENDING).limit(10)
        description = ''
        for i, user in enumerate(results):
            member = self.bot.get_user(user["_id"])
            if not member:
                member = 'Unbekannt'
            description += f'`[{i + 1}]` | **{member}** ({user["balance"]})\n'
        await ctx.send(embed=discord.Embed(
            color=discord.Color.green(),
            title=':dollar: Die reichsten Member:',
            description=description
        ))

    @commands.command(usage='transfer <user> <amount>', aliases=['give'])
    @commands.cooldown(1, 3, commands.BucketType.channel)
    @commands_or_casino_only()
    async def transfer(self, ctx, user: discord.User, amount):
        """Gibt jemandem Geld"""
        if user.bot:
            await ctx.send(embed=discord.Embed(
                color=discord.Color.red(),
                title='Dieses Mitglied hat kein Geld',
                description='Bots sind leider davon ausgeschlossen, aber trotzdem danke, dass du ihnen Geld geben wolltest :)'
            ))
            return
        bal = self.con["stats"].find_one({"_id": ctx.author.id}, {"balance": 1})["balance"]
        if amount.isdigit():
            amount = int(amount)
        elif amount in ['max', 'all']:
            amount = bal
        else:
            await ctx.send(embed=discord.Embed(
                color=discord.Color.red(),
                title=f'Wie viel Geld willst du {user.name} geben?',
                description='Bitte gib eine **Zahl** "**all**" oder "**max**" an'
            ))
            return
        if amount > bal:
            await ctx.send(f"{ctx.author.mention} Du hast nicht genügend Bargeld")
        elif amount < 1:
            await ctx.send(f"{ctx.author.mention} Du musst mindestens 1 :dollar: angeben")
        else:
            self.con["stats"].update({"_id": ctx.author.id}, {"$inc": {"balance": -amount}})
            self.con["stats"].update({"_id": user.id}, {"$inc": {"balance": amount}})
            await ctx.send(f"Du hast {user.mention} **{amount}** :dollar: gegeben")

    @commands.command(usage='rob <user>', aliases=['steal'])
    @commands.cooldown(1, 300, commands.BucketType.user)
    @commands_or_casino_only()
    async def rob(self, ctx, user: discord.User):
        """Raubt jemanden aus"""
        if user.bot:
            await ctx.send("Du kannst keine Bots ausrauben")
            return
        ybal = self.con["stats"].find_one({"_id": ctx.author.id}, {"balance": 1})["balance"]
        ubal = self.con["stats"].find_one({"_id": user.id}, {"balance": 1})["balance"]
        if ybal < 100:
            await ctx.send(f"{ctx.author.mention} Du brauchst mindestens 100 :dollar:, um jemanden ausrauben zu können")
        elif ubal < 200:
            await ctx.send(f"{ctx.author.mention} Dieser Nutzer hat weniger als 200 :dollar:. Das lohnt sich nicht")
        else:
            chance = random.randint(1, 100)
            per = ybal / ubal * 100
            if per > 30:
                per = 30
            elif per < 10:
                per = 10
            if per > chance:
                if chance > 50:
                    chance = 50
                elif chance < 20:
                    chance = 20
                rob = int(ubal * chance / 100)
                self.con["stats"].update({"_id": ctx.author.id}, {"$inc": {"balance": rob}})
                self.con["stats"].update({"_id": user.id}, {"$inc": {"balance": -rob}})
                await ctx.send(
                    f'Du konntest von {user.mention} **{rob}** :dollar: stehlen, ohne dass er es bemerkt hat.')
            else:
                pay = random.randint(75, 100)
                self.con["stats"].update({"_id": ctx.author.id}, {"$inc": {"balance": -pay}})
                self.con["stats"].update({"_id": user.id}, {"$inc": {"balance": pay}})
                await ctx.send(f'Du wurdest erwischt und musstest {user.mention} **{pay}** :dollar: Strafe zahlen!')

    @commands.command(aliases=["claim"])
    @commands.cooldown(1, 79200, commands.BucketType.user)
    @commands_or_casino_only()
    async def daily(self, ctx):
        """Hole dir deine tägliche Belohnung ab"""
        add = random.randint(250, 450)
        self.con["stats"].update({"_id": ctx.author.id}, {"$inc": {"balance": add}})
        await ctx.send(embed=discord.Embed(
            color=discord.Color.green(),
            title='Belohnung abgeholt',
            description=f'Du hast **{add}** :dollar: erhalten :tada:'
        ))

    @commands.command(usage="set <user> <balance>", hidden=True)
    @commands.cooldown(1, 3, commands.BucketType.user)
    @owner_only()
    async def set(self, ctx, user: discord.User, balance: int):
        """Ändert die Bilanz von einem Nutzer"""
        self.con["stats"].update({"_id": user.id}, {"$set": {"balance": balance}})
        await ctx.send(embed=discord.Embed(
            color=discord.Color.green(),
            title="Erfolgreich",
            description=f"Die Bilanz von **{user.name}** wurde auf **{balance}** gesetzt."
        ))


def setup(bot):
    bot.add_cog(Currency(bot))
