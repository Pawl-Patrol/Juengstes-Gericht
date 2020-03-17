import discord
from discord.ext import commands
from utils.checks import min_lvl, commands_only
from utils.chatbot import NewChatBot
import asyncio
from main import con
import urllib.parse as parse
import upsidedown
import random


class Fun(commands.Cog, command_attrs=dict(cooldown_after_parsing=True)):

    def __init__(self, bot):
        self.emoji = ":rocket:"
        self.bot = bot
        self.ChatBot = NewChatBot()

    @commands.command(enabled=False, usage="marry <user>")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def marry(self, ctx, user: discord.User):
        """Heiratet ein Mitglied"""
        marry = con["stats"].find_one({"_id": ctx.author.id}, {"married_to": 1})["married_to"]
        umarry = con["stats"].find_one({"_id": user.id}, {"married_to": 1})["married_to"]
        if marry:
            await ctx.send(embed=discord.Embed(
                color=discord.Color.red(),
                title="Du bist schon verheiratet",
                description=f"Benutze `{ctx.prefix}divorce`, bevor du wieder jemanden heiraten kannst"
            ))
        elif umarry:
            await ctx.send(embed=discord.Embed(
                color=discord.Color.red(),
                title="Dieser Nutzer ist schon verheiratet",
                description=f"Tut mir leid für dich :/"
            ))
        elif ctx.author.id == user.id:
            await ctx.send(embed=discord.Embed(
                color=discord.Color.red(),
                title="Du kannst dich nicht selbst heiraten :/",
                description=f"Tut mir leid, dass du so einsam bist *hug*"
            ))
        elif user.bot:
            await ctx.send(embed=discord.Embed(
                color=discord.Color.red(),
                title="Du kannst keinen Bot heiraten :/",
                description=f"Tut mir leid, dass du so einsam bist *hug*"
            ))
        else:
            await ctx.send(f"{user.mention}, Willst du **{ctx.author.name}** heiraten? :ring:")
            while True:
                try:
                    message = await self.bot.wait_for("message", check=lambda m: m.author.id == user.id, timeout=20)
                except asyncio.TimeoutError:
                    await ctx.send(f"{ctx.author.mention}, Leider hat **{user.name}** nicht rechtzeitig geantwortet :/")
                    return
                if message.content.lower().split(" ")[0] in ["j", "ja", "y", "ye", "yes", "yesu", "yea", "ok", "okay", "oki", "oke", "ya", "yas", "sure"]:
                    break
                elif message.content.lower().split(" ")[0] in ["n", "no", "nu", "nein", "nah", "ne", "nö", "nope", "nej"]:
                    await ctx.send(f"{user.mention} möchte dich nicht heiraten :/ Der Vorgang wurde abgebrochen.")
                    return
            con["stats"].update({"_id": ctx.author.id}, {"$set": {"married_to": user.id}})
            con["stats"].update({"_id": user.id}, {"$set": {"married_to": ctx.author.id}})
            await ctx.send(embed=discord.Embed(
                color=discord.Color.green(),
                title="Herzlichen Glückwunsch :tada:",
                description=f"{ctx.author.mention} und {user.mention} sind jetzt verheiratet! :ring:"
            ))

    @commands.command(enabled=False)
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def divorce(self, ctx):
        """Trennt dich von deinem Partner"""
        marry = con["stats"].find_one({"_id": ctx.author.id}, {"married_to": 1})["married_to"]
        if not marry:
            await ctx.send(embed=discord.Embed(
                color=discord.Color.red(),
                title="Du bist noch nicht verheiratet",
                description=f"Benutze `{ctx.prefix}marry <user>`, um jemanden zu heiraten"
            ))
        else:
            con["stats"].update({"_id": ctx.author.id}, {"$set": {"married_to": 0}})
            con["stats"].update({"_id": marry}, {"$set": {"married_to": 0}})
            await ctx.send("Du hast dich von <@{marry}> geschieden! :broken_heart:")

    @commands.command(usage="pornhub <text>", aliases=["ph"])
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def pornhub(self, ctx, *, text):
        """Sucht auf Pornhub nach dem angegebenem Text"""
        await ctx.send("https://www.pornhub.com/video/search?search=" + parse.quote_plus(text))

    @commands.command(usage="google <text>")
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def google(self, ctx, *, text):
        """Sucht auf Pornhub nach dem angegebenem Text"""
        await ctx.send("https://www.google.com/search?q=" + parse.quote_plus(text))

    @commands.command(usage="vote <question>", aliases=["v"])
    @commands.cooldown(1, 30, commands.BucketType.channel)
    @min_lvl(20)
    async def vote(self, ctx, *, text):
        """Startet eine Abstimmung"""
        if text[-1] != "?":
            text += "?"
        embed = discord.Embed(
            color=discord.Color.green(),
            title=discord.utils.escape_mentions(text)
        )
        embed.set_footer(text=f"Eine Abstimmung von {ctx.author}")
        msg = await ctx.send(embed=embed)
        await msg.add_reaction('<:upvote:660605232019144705>')
        await msg.add_reaction('<:downvote:660605265783291914>')

    @commands.command(aliases=["respects", "f"])
    @commands.cooldown(1, 10, commands.BucketType.channel)
    async def respect(self, ctx):
        """Gib jemandem Respekt"""
        msg = await ctx.send("Press F to pay respects")
        await msg.add_reaction("🇫")

    @commands.command(usage="flip <text>")
    @commands.cooldown(1, 10, commands.BucketType.channel)
    async def flip(self, ctx, *, text):
        """Dreht deinen Text um"""
        await ctx.send(upsidedown.transform(discord.utils.escape_mentions(text)))

    @commands.command(aliases=['lovecalc'])
    async def ship(self, ctx, user1: discord.User, user2: discord.User):
        """Berechnet die Liebe zwischen 2 Personen"""
        ship = random.randint(0, 100)
        bar = round(ship / 10) * '▰' + (10 - round(ship / 10)) * '▱'
        await ctx.send(embed=discord.Embed(color=0xFF0000, title=f':heart: Lovecalculator', description=f'[{bar}](https://www.youtube.com/watch?v=WiinVuzh4DA) **{ship}%**\n**{user1.display_name}** & **{user2.display_name}**'))

    @commands.command(aliases=['chatbot'])
    @commands_only()
    @commands.cooldown(1, 60, commands.BucketType.channel)
    async def chat(self, ctx):
        def create_embed(text):
            text = text.replace("#PUNKT#", ".")
            embed = discord.Embed(
                color=discord.Color.purple(),
                title=f":robot: ChatBot (Alpha)",
                description=f"~ {text[:1].capitalize() + text[1:]}"
            )
            return embed
        trigger = "Hallo! Wie kann ich dir helfen?"
        while True:
            msg = await ctx.send(embed=create_embed(trigger))
            try:
                message = await ctx.bot.wait_for("message", check=lambda m: m.author == ctx.author and m.channel == ctx.channel, timeout=60)
            except asyncio.TimeoutError:
                await msg.edit(embed=create_embed("Sitzung beendet."))
                return
            response = message.content.lower()
            self.ChatBot.process_response(trigger, response)
            trigger = self.ChatBot.get_response(response)

    @commands.command()
    @commands_only()
    async def chatbotentry(self, ctx, trigger: str, response: str):
        embed = discord.Embed(
            color=discord.Color.orange(),
            title="Neuer ChatBot Eintrag",
            description=f"**Trigger**: {trigger}\n**Response**: {response}"
        )
        msg = await ctx.send(embed=embed)
        reactions = ["✅", "❌"]
        for r in reactions:
            await msg.add_reaction(r)
        try:
            reaction, user = await ctx.bot.wait_for("reaction_add", check=lambda r, u: r.message.id == msg.id and u == ctx.author and str(r.emoji) in reactions, timeout=60)
        except asyncio.TimeoutError:
            embed.color = discord.Color.red()
            await msg.edit(embed=embed)
            await msg.clear_reactions()
            return
        await msg.clear_reactions()
        if str(reaction.emoji) == reactions[0]:
            embed.color = discord.Color.green()
            await msg.edit(embed=embed)
            self.ChatBot.process_response(trigger, response)
        elif str(reaction.emoji) == reactions[1]:
            embed.color = discord.Color.red()
            await msg.edit(embed=embed)


def setup(bot):
    bot.add_cog(Fun(bot))
