from discord.ext import commands
from main import lvlcalc, con
import datetime
import json

with open("data/config.json", "r") as f:
    config = json.load(f)
cmds = config["commands_channel"]
casino = config["casino_channel"]


def owner_only():
    async def predicate(ctx):
        return ctx.author.id == ctx.bot.owner_id

    return commands.check(predicate)


def mute_perms():
    async def predicate(ctx):
        serverteam = ctx.guild.get_role(config["serverteam_role"])
        return serverteam in ctx.author.roles

    return commands.check(predicate)

def min_lvl(lvl):
    async def predicate(ctx):
        stats = con["stats"].find_one({"_id": ctx.author.id})
        level, _, _ = lvlcalc(stats["total_xp"])
        if level >= lvl or ctx.author.guild_permissions.administrator:
            return True
        return False

    return commands.check(predicate)


def commands_only():
    async def predicate(ctx):
        return ctx.channel.id == cmds or ctx.guild.id == 590976073555116081

    return commands.check(predicate)


def casino_only():
    async def predicate(ctx):
        if ctx.channel.id != casino and ctx.guild.id != 590976073555116081:
            raise commands.CommandError(f'Gambling ist nur in <#{casino}> verfügbar')
        return True

    return commands.check(predicate)


def commands_or_casino_only():
    async def predicate(ctx):
        return ctx.channel.id == cmds or ctx.channel.id == casino or ctx.guild.id == 590976073555116081

    return commands.check(predicate)


def has_item(item):
    async def predicate(ctx):
        inv = con["inventory"].find_one({"_id": ctx.author.id})
        if item in inv:
            return True
        else:
            raise commands.CheckFailure(f"Du brauchst mindestens **1x {item.title()}**, um diesen Command nutzen zu können")

    return commands.check(predicate)

def has_pet():
    async def predicate(ctx):
        pet = con["pets"].find_one({"_id": ctx.author.id})
        if not pet:
            tn = datetime.datetime.utcnow() - datetime.timedelta(minutes=15)
            post = {
                "_id": ctx.author.id,
                "url": "https://cdn.discordapp.com/attachments/593494518305914900/687695850377445393/offended_owl.png",
                "name": f"{ctx.author.name}'s Pet",
                "xp": 0,
                "hunger": tn,
                "hygiene": tn,
                "fun": tn,
                "energy": tn
            }
            con["pets"].insert_one(post)
        return True

    return commands.check(predicate)
