import discord
from discord.ext import commands, timers
from utils.checks import mute_perms, min_lvl
from utils.converters import duration
import datetime
import asyncio
import json


class Moderation(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.timer_manager = timers.TimerManager(bot)
        with open("data/config.json", "r") as f:
            self.config = json.load(f)

    @commands.command(usage='clear [limit] [user]', aliases=['clean', 'purge', 'nuke'])
    @commands.has_permissions(manage_messages=True)
    async def clear(self, ctx, limit: int = 100, member: discord.Member = None):
        """Löscht x Nachrichten (von einem Nutzer)"""
        await ctx.message.delete()
        if member:
            deleted = await ctx.channel.purge(limit=limit + 1, check=lambda m: m.author == member)
        else:
            deleted = await ctx.channel.purge(limit=limit)
        await ctx.send(f'**{len(deleted)}** Nachrichten wurden gelöscht', delete_after=2)

    @commands.command(usage='ban <member> [reason]', aliases=['bann'])
    @commands.has_permissions(ban_members=True)
    async def ban(self, ctx, member: discord.Member, *, reason: str = None):
        """Bannt jemanden vom Server"""
        if ctx.author.top_role.position <= member.top_role.position and ctx.author != ctx.guild.owner:
            await ctx.send(embed=discord.Embed(
                color=discord.Color.red(),
                title='Command-Error',
                description='Du kannst niemanden bannen, der über dir steht oder die gleiche Position hat wie du'
            ))
            return
        if reason is None:
            reason = f'Kein Grund angegeben'
        await ctx.guild.ban(member, reason=reason)
        await ctx.send(embed=discord.Embed(
            color=discord.Color.green(),
            title=':hammer: Bann',
            description=f'**{member.name}** wurde gebannt'
        ))

    @commands.command(usage='ban <member> [reason]')
    @commands.has_permissions(kick_members=True)
    async def kick(self, ctx, member: discord.Member, *, reason: str = None):
        """Kickt jemanden vom Server"""
        if ctx.author.top_role.position <= member.top_role.position and ctx.author != ctx.guild.owner:
            await ctx.send(embed=discord.Embed(
                color=discord.Color.red(),
                title='Command-Error',
                description='Du kannst niemanden kicken, der über dir steht oder die gleiche Position hat wie du'
            ))
            return
        if reason is None:
            reason = f'Kein Grund angegeben'
        await ctx.guild.kick(member, reason=reason)
        await ctx.send(embed=discord.Embed(
            color=discord.Color.green(),
            title=':boot: Kick',
            description=f'**{member.name}** wurde gekickt'
        ))

    @commands.command(usage='mute <member> [duration]')
    @mute_perms()
    async def mute(self, ctx, member: discord.Member, *, duration: duration = (600, '10m')):
        """Mutet jemanden vom Server"""
        mute_role = discord.utils.get(ctx.guild.roles, id=self.config["mute_role"])
        if ctx.author.top_role.position <= member.top_role.position and ctx.author.id != ctx.guild.owner.id:
            await ctx.send(embed=discord.Embed(
                color=discord.Color.red(),
                title='Command-Error',
                description='Du kannst niemanden muten, der über dir steht oder die gleiche Position hat wie du'
            ))
        elif mute_role in member.roles:
            await ctx.send(embed=discord.Embed(
                color=discord.Color.red(),
                title='Command-Error',
                description='Dieser Nutzer ist bereits gemutet'
            ))
        else:
            await member.add_roles(mute_role)
            self.timer_manager.create_timer('mute_expire', datetime.timedelta(seconds=duration[0]), args=(member, mute_role))
            await ctx.send(embed=discord.Embed(
                color=discord.Color.green(),
                title=':mute: Mute',
                description=f'**{member.display_name}** wurde für `{duration[1]}` gemuted'
            ))

    @commands.command(usage='votemute <member>', aliases=['vm'])
    @min_lvl(25)
    async def votemute(self, ctx, member: discord.Member):
        """Startet ein Abstimmung, ob jemand gemutet werden soll"""
        mute_role = discord.utils.get(ctx.guild.roles, id=self.config["mute_role"])
        if ctx.author.top_role.position <= member.top_role.position and ctx.author.id != ctx.guild.owner.id:
            await ctx.send(embed=discord.Embed(
                color=discord.Color.red(),
                title='Command-Error',
                description='Du kannst niemanden votemuten, der über dir steht oder die gleiche Position hat wie du'
            ))
        elif mute_role in member.roles:
            await ctx.send(embed=discord.Embed(
                color=discord.Color.red(),
                title='Command-Error',
                description='Dieser Nutzer ist bereits gemutet'
            ))
        else:
            msg = await ctx.send(embed=discord.Embed(
                color=discord.Color.blurple(),
                title='Abstimmung',
                description=f'Soll **{member.display_name}** für `10m` gemutet werden?'
            ))
            reactions = {
                '<:upvote:660605232019144705>': 0,
                '<:downvote:660605265783291914>': 0
            }
            for reaction in reactions:
                await msg.add_reaction(reaction)
            while True:
                try:
                    reaction, user = await ctx.bot.wait_for('reaction_add', check=lambda r, u: r.message.id == msg.id and u.id != ctx.bot.user.id, timeout=10)
                except asyncio.TimeoutError:
                    break
                for msg_reaction in reaction.message.reactions:
                    users = await msg_reaction.users().flatten()
                    if user in users and msg_reaction.emoji != reaction.emoji or not str(msg_reaction.emoji) in reactions:
                        await reaction.message.remove_reaction(msg_reaction, user)
            msg = await ctx.channel.fetch_message(msg.id)
            for reaction in msg.reactions:
                if str(reaction.emoji) in reactions:
                    reactions[str(reaction.emoji)] = reaction.count
            yes = reactions['<:upvote:660605232019144705>']
            no = reactions['<:downvote:660605265783291914>']
            if yes > no:
                color = discord.Color.green()
                description = f"**{member.display_name}** wurde für `10m` gemutet"
                await member.add_roles(mute_role)
                self.timer_manager.create_timer("mute_expire", datetime.timedelta(minutes=10), args=(member, mute_role))
            else:
                color = discord.Color.red()
                description = f"\n\n**{member.display_name}** wurde nicht gemutet"
            await msg.edit(embed=discord.Embed(
                color=color,
                title='Abstimmung zuende',
                description=description
            ))

    @commands.command(usage='unmute <member>')
    @mute_perms()
    async def unmute(self, ctx, member: discord.Member):
        """Entmutet jemanden vom Server"""
        mute_role = discord.utils.get(ctx.guild.roles, id=self.config["mute_role"])
        if ctx.author.top_role.position <= member.top_role.position and ctx.author != ctx.guild.owner:
            await ctx.send(embed=discord.Embed(
                color=discord.Color.red(),
                title='Command-Error',
                description='Du kannst niemanden entmuten, der über dir steht oder die gleiche Position hat wie du'
            ))
        elif mute_role not in member.roles:
            await ctx.send(embed=discord.Embed(
                color=discord.Color.red(),
                title='Command-Error',
                description='Dieser Nutzer ist nicht gemutet'
            ))
        else:
            await member.remove_roles(mute_role)
            await ctx.send(embed=discord.Embed(
                color=discord.Color.green(),
                title=':loud_sound: Unmute',
                description=f'**{member.display_name}** wurde entmuted'
            ))

    @commands.command()
    async def selfmute(self, ctx):
        """Mutet dich selbst für 10 Minuten"""
        mute_role = discord.utils.get(ctx.guild.roles, id=self.config["mute_role"])
        await ctx.author.add_roles(mute_role)
        self.timer_manager.create_timer('mute_expire', datetime.timedelta(minutes=10), args=(ctx.author, mute_role))
        await ctx.send(embed=discord.Embed(
            color=discord.Color.green(),
            title=':mute: Selfmute',
            description=f'Du wurdest für `10m` gemuted'
        ))

    @commands.command()
    @commands.has_permissions(manage_nicknames=True)
    async def nick(self, ctx, member: discord.Member, *, nick):
        """Ändert den Nickname eines Members"""
        if ctx.author.top_role.position <= member.top_role.position and ctx.author.id != ctx.guild.owner.id:
            await ctx.send(embed=discord.Embed(
                color=discord.Color.red(),
                title='Command-Error',
                description=f'Du kannst den Nickname von **{member}** nicht ändern, da er über dir steht oder die selbe Position hat wie du.'
            ))
        else:
            await member.edit(nick=nick)
            await ctx.message.add_reaction("✨")

    @commands.Cog.listener()
    async def on_mute_expire(self, member, mute_role):
        """Wird ausgeführt wenn die Stummschaltung abgelaufen ist"""
        await member.remove_roles(mute_role)


def setup(bot):
    bot.add_cog(Moderation(bot))
