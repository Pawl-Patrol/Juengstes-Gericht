import discord
from discord.ext import commands
import datetime


def help_check():
    async def predicate(ctx):
        if ctx.guild.id == 680052595322388507:
            print('test')
            return ctx.channel.id == 680134524788801536
        return True

    return commands.check(predicate)


class HelpCommand(commands.HelpCommand):

    def __init__(self):
        super().__init__(
            verify_checks=False,
            command_attrs={
                'checks': [help_check()],
                'cooldown': commands.Cooldown(1, 3, commands.BucketType.member),
                'help': 'Gibt dir Hilfe zu den Commands',
                'aliases': ['h', 'commands', 'cmds'],
                'hidden': True
            })

    async def command_not_found(self, string):
        return f'Ich konnte keinen Command mit dem Namen "{string}" finden'

    async def send_error_message(self, error):
        await self.context.send(embed=discord.Embed(
            color=discord.Color.red(),
            title='Ein Fehler ist aufgetreten :/',
            description=error
        ))

    async def send_bot_help(self, mapping):
        embed = discord.Embed(
            color=discord.Color.blue(),
            description=f"**[Server Invite](https://discord.gg/eJ8rfpr)**\nServer Prefix: `{self.clean_prefix.replace(' ', '')}`\nFür mehr Info, nutze `{self.clean_prefix}help <command>`\n"
        )
        total = 0
        for cog_name, cog in self.context.bot.cogs.items():
            cmds = sorted(cog.get_commands(), key=lambda c: c.name)
            if len(cmds) == 0:
                continue
            total += len(cmds)
            cmd_string = " ".join([f"`{c.name}`" for c in cmds])
            embed.description += f"\n**{cog.emoji} {cog_name.upper()}** ({len(cmds)} Commands)\n{cmd_string}\n"
        embed.title = f'Alle Commands ({total} Commands)'
        embed.set_footer(text=f"{self.context.guild.name} ({self.context.guild.member_count} Mitglieder)")
        embed.timestamp = datetime.datetime.utcnow()
        await self.context.send(embed=embed)

    async def send_cog_help(self, cog):
        entries = await self.filter_commands(cog.get_commands(), sort=True)
        description = ''
        for command in entries:
            description += f'`{command.name}`, '
        await self.context.send(embed=discord.Embed(
            color=discord.Color.blue(),
            title=f'{cog.qualified_name.title()} ({len(entries)} Commands)',
            description=description[:-2]
        ))

    async def send_group_help(self, group):
        subcommands = group.commands
        if len(subcommands) == 0:
            return await self.send_command_help(group)
        entries = await self.filter_commands(subcommands, sort=True)
        embed = discord.Embed(
            color=discord.Color.blue(),
            title=f'{group.qualified_name.title()} ({len(entries)} Commands)',
            description=group.help
        )
        for command in entries:
            usage = command.usage
            if not usage:
                usage = command.name
            embed.add_field(name=usage, value=command.help, inline=False)
        await self.context.send(embed=embed)

    async def send_command_help(self, command):
        embed = discord.Embed(
            color=discord.Color.blue(),
            title='Command-Hilfe',
            description=command.help if command.help else f'Infos zum Command "**{command.name}**"'
        )

        usage = command.usage
        if not usage:
            usage = command.qualified_name
        embed.add_field(name='Verwendung:', value=f'`{self.clean_prefix}{usage}`', inline=False)

        if command.aliases:
            embed.add_field(name='Aliase:', value='`' + '`, `'.join(command.aliases) + '`', inline=False)

        cooldown = command._buckets._cooldown
        if cooldown:
            embed.add_field(name='Cooldown:', value=f'**{int(cooldown.per)}** Sekunden', inline=False)
        await self.context.send(embed=embed)
