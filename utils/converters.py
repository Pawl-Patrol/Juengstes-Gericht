from discord.ext import commands
from main import connection as con
import re


class duration(commands.Converter):
    async def convert(self, ctx, argument):
        duration = {
            'weeks': 0,
            'days': 0,
            'hours': 0,
            'minutes': 0,
            'seconds': 0
        }
        string = ''
        for trigger in duration:
            arg = re.search(rf'\d+({trigger}?|{trigger[0]})', argument.lower())
            if arg:
                match = re.search(r'\d+', arg.group(0))
                hl = int(match.group(0))
                duration[trigger] = hl
                string += str(hl) + trigger[0]
        seconds = 0
        seconds += duration['seconds']
        seconds += duration['minutes'] * 60
        seconds += duration['hours'] * 3600
        seconds += duration['days'] * 86400
        seconds += duration['weeks'] * 604800
        if not seconds:
            arg = re.search(r'\d+', argument)
            if arg:
                hl = int(arg.group(0))
                seconds += hl * 60
                string += str(hl) + 'm'
            else:
                raise commands.BadArgument(
                    'Die angegebene Zeit ist ungültig. Nutze folgendes Format: z.B. `10m` oder `1h`')
        return seconds, string


class bet(commands.Converter):
    async def convert(self, ctx, argument):
        bal = con["stats"].find_one({"_id": ctx.author.id}, {"balance": 1})["balance"]
        if argument.isdigit():
            argument = int(argument)
        elif argument.lower() == 'all' or argument.lower() == 'max':
            argument = bal
        else:
            raise commands.BadArgument('Bitte gib eine **Anzahl** oder "**all**" an')
        if bal < argument:
            raise commands.CommandError('Du hast nicht genügend Geld')
        elif argument < 1:
            raise commands.CommandError('Du musst mindestens **1** :dollar: setzen')
        else:
            return argument


class is_item(commands.Converter):
    async def convert(self, ctx, argument):
        item = con["items"].find_one({"_id": argument.lower()})
        if item:
            return item
        else:
            item = con["tools"].find_one({"_id": argument.lower()})
            if item:
                return item
            elif ctx.command.name == "sell" and argument.lower() == "all":
                return "all"
            else:
                raise commands.BadArgument('Item konnte nicht gefunden werden')
