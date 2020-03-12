import discord
from discord.ext import commands
from main import connection as con
from utils.checks import commands_only, has_pet
from utils.utils import convert_pet, lvlcalc
import random
import datetime


class Pets(commands.Cog, command_attrs=dict(cooldown_after_parsing=True)):

    def __init__(self, bot):
        self.bot = bot
        self.con = con

    @commands.group(case_insensitive=True)
    #@commands_only()
    @has_pet()
    @commands.cooldown(1, 2, commands.BucketType.user)
    async def pet(self, ctx):
        """Zeigt dir Informationen über dein Pet"""
        if ctx.invoked_subcommand is None:
            pet = self.con["pets"].find_one({"_id": ctx.author.id})
            stats = convert_pet(pet)
            embed = discord.Embed(
                color=discord.Color.greyple(),
                title=pet["name"],
                description=f"Nutze `{ctx.prefix}help pet` für mehr Info"
            )
            embed.set_thumbnail(url=pet["url"])
            for stat, val in stats.items():
                bar = "▰" * int(val/10) + "▱" * (10-int(val/10))
                embed.add_field(name=stat.title() + f" ({val}%)", value=bar, inline=False)
            level, xp, cap = lvlcalc(pet["xp"])
            per = xp/cap * 10
            string = "▰" * int(per) + "▱" * (10-int(per))
            bar = f"[{string}](https://www.youtube.com/watch?v=DyDfgMOUjCI&list=RD2G1Bnwsw7lA&index=10)\n`Level {level+1}`"
            embed.add_field(name=f"Erfahrung ({xp}/{cap})", value=bar)
            await ctx.send(embed=embed)

    @pet.command(usage="name <name>")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def name(self, ctx, *, name: str):
        """Benennt dein Pet um"""
        if len(name) > 25:
            await ctx.send(f"{ctx.author.mention} Der Name darf nicht länger als 25 Zeichen sein.")
        else:
            self.con["pets"].update({"_id": ctx.author.id}, {"$set": {"name": name}})
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
            self.con["pets"].update({"_id": ctx.author.id}, {"$set": {"url": url}})
        except discord.HTTPException:
            await ctx.send(f"{ctx.author.mention} Bitte gib eine gültige URL an.")

    @pet.command()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def feed(self, ctx):
        """Füttert dein Pet"""
        result = await pet_action(ctx, "hunger")
        if result:
            await ctx.send(f"{ctx.author.mention} Du hast dein Pet für **{result}** Dollar gefüttert.")
        else:
            await ctx.send(f"{ctx.author.mention} Bitte warte noch, bevor du dein Pet füttern kannst.")

    @pet.command()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def wash(self, ctx):
        """Wäscht dein Pet"""
        result = await pet_action(ctx, "hygiene")
        if result:
            await ctx.send(f"{ctx.author.mention} Du hast dein Pet für **{result}** Dollar gewaschen.")
        else:
            await ctx.send(f"{ctx.author.mention} Bitte warte noch, bevor du dein Pet waschen kannst.")

    @pet.command()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def play(self, ctx):
        """Spiele mit deinem Pet"""
        result = await pet_action(ctx, "fun", cost=False)
        if result:
            await ctx.send(f"{ctx.author.mention} Du hast mit deinem Pet gespielt. **+{result} XP**")
        else:
            await ctx.send(f"{ctx.author.mention} Bitte warte noch, bevor du mit deinem Pet spielen kannst.")

    @pet.command()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def train(self, ctx):
        """Trainiere dein Pet"""
        result = await pet_action(ctx, "energy", cost=False)
        if result:
            await ctx.send(f"{ctx.author.mention} Du hast dein Pet trainiert. **+{result} XP**")
        else:
            await ctx.send(f"{ctx.author.mention} Bitte warte noch, bevor du dein Pet trainieren kannst.")


async def pet_action(ctx, action, cost: bool = True):
    bal = con["stats"].find_one({"_id": ctx.author.id}, {"balance": 1})["balance"]
    pet = con["pets"].find_one({"_id": ctx.author.id})
    stats = convert_pet(pet)
    if bal < 50:
        raise commands.CommandError(f"{ctx.author.mention} Du brauchst mindestens **50** Dollar.")
    elif stats[action] > 80:
        return False
    else:
        dif = 100 - (stats[action] + random.randint(25, 35))
        if dif < 0:
            dif = 0
        t = datetime.datetime.utcnow() - datetime.timedelta(seconds=20*dif)
        xp = random.randint(15, 25)
        con["pets"].update({"_id": ctx.author.id}, {"$set": {action: t}, "$inc": {"xp": xp}})
        if cost:
            cost = random.randint(35, 50)
            con["stats"].update({"_id": ctx.author.id}, {"$inc": {"balance": -cost}})
            return cost
        else:
            return xp


def setup(bot):
    bot.add_cog(Pets(bot))
