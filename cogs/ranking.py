import discord
from discord.ext import commands
from main import connection, lvlcalc
from utils.checks import commands_only
import json
from aiohttp import ClientSession
import time
from PIL import Image
from PIL import ImageFont
from PIL import ImageDraw
from io import BytesIO
import pymongo
import asyncio


class Ranking(commands.Cog, command_attrs=dict(cooldown_after_parsing=True)):
    def __init__(self, bot):
        self.bot = bot
        self.con = connection
        with open("data/config.json", "r") as f:
            self.config = json.load(f)
        self.session = ClientSession(loop=bot.loop)

    async def get_avatar(self, user):
        avatar_url = user.avatar_url_as(format="png", size=512)
        async with self.session.get(str(avatar_url)) as response:
            avatar_bytes = await response.read()
        return avatar_bytes

    @commands.command()
    @commands.cooldown(3, 10, commands.BucketType.user)
    async def ping(self, ctx):
        """Pong! Gibt die Reaktionszeit des Bots zurück"""
        before = time.monotonic()
        message = await ctx.send("***Pinging...***")
        ping = (time.monotonic() - before) * 1000
        await message.edit(content=f"**Pong!** `{int(ping)}ms`")

    @commands.command(usage='rank [user]', aliases=['profile'])
    @commands.cooldown(1, 10, commands.BucketType.user)
    @commands_only()
    async def rank(self, ctx, user: discord.User = None):
        """Zeigt deinen Rang oder den Rang eines anderen Mitglieds"""
        if user is None:
            user = ctx.author
        if user.bot:
            await ctx.send("Ich kann keine Ränge von Bots anzeigen")
            return

        async with ctx.typing():
            stats = self.con["stats"].find_one({"_id": user.id})
            level, xp, cap = lvlcalc(stats["total_xp"])
            img = Image.open("data/media/rank_card.png")
            draw = ImageDraw.Draw(img)
            fontsmall = ImageFont.truetype("data/monospace.ttf", 50)
            font = ImageFont.truetype("data/monospace.ttf", 70)
            fontbig = ImageFont.truetype("data/monospace.ttf", 100)
            fontbigger = ImageFont.truetype("data/monospace.ttf", 250)
            draw.rectangle(((452, 350), (452 + int(xp / cap * 850), 435)), fill=(119, 221, 119))
            draw.text((100, 90), "LEVEL", (255, 255, 255), font=fontbig)
            w, h = draw.textsize(str(level), font=fontbigger)
            draw.text(((500 - w) / 2, 190), str(level), (255, 255, 255), font=fontbigger)
            w, h = draw.textsize(f"{xp}/{cap}", font=fontsmall)
            draw.text((452 + (850 - w) / 2, 365), f"{xp}/{cap}", (255, 255, 255), font=fontsmall)
            draw.text((450, 110), f"Text-XP: {stats['message_xp']}", (255, 255, 255), font=font)
            draw.text((450, 220), f"Voice-XP: {stats['voice_xp']}", (255, 255, 255), font=font)
            avatar_bytes = await self.get_avatar(user)
            with Image.open(BytesIO(avatar_bytes)) as im:
                im = im.resize((400, 400))
                rgb_avatar = im.convert("RGB")
                with Image.new("L", im.size, 0) as mask:
                    mask_draw = ImageDraw.Draw(mask)
                    mask_draw.ellipse([(0, 0), im.size], fill=255)
                    img.paste(rgb_avatar, (1450, 70), mask=mask)
            img.save('generated_data/rank_gen.png')
            file = discord.File("generated_data/rank_gen.png")
            await ctx.send(file=file, content=f":clipboard: | **Rang von {user}**")

    @commands.command(usage='leaderboard [page]', aliases=['lb', 'top'])
    @commands.cooldown(1, 10, commands.BucketType.guild)
    @commands_only()
    async def leaderboard(self, ctx, page: int = 1):
        """Zeigt alle Member sortiert nach ihren XP"""
        results = list(self.con["stats"].find({}).sort("total_xp", pymongo.DESCENDING))
        pages, b = divmod(len(results), 10)
        if b:
            pages += 1
        if page > pages:
            page = pages
        elif page < 1:
            page = 1

        def create_embed(lb_page):
            description = ''
            i = (lb_page - 1) * 10 + 1
            for result in results[(lb_page - 1) * 10:lb_page * 10]:
                member = self.bot.get_user(result["_id"])
                if not member:
                    member = 'Unbekannt'
                description += f'`[{i}]` | **{member}** ({result["total_xp"]})\n'
                i += 1
            embed = discord.Embed(
                color=discord.Color.blurple(),
                title=f"Leaderboard ({lb_page}/{pages})",
                description=description
            )
            embed.set_thumbnail(url=ctx.guild.icon_url)
            return embed

        menu = await ctx.send(embed=create_embed(page))
        if pages > 1:
            reactions = ['◀', '⏹', '▶']
            for reaction in reactions:
                await menu.add_reaction(reaction)

            def check(r, u):
                return r.message.id == menu.id and u == ctx.author and str(r.emoji) in reactions

            while True:
                try:
                    reaction, user = await ctx.bot.wait_for("reaction_add", check=check, timeout=60)
                except asyncio.TimeoutError:
                    await menu.delete()
                    return
                await menu.remove_reaction(reaction, user)
                if str(reaction.emoji) == reactions[0] and page > 1:
                    page -= 1
                    await menu.edit(embed=create_embed(page))
                elif str(reaction.emoji) == reactions[1]:
                    await menu.delete()
                    return
                elif str(reaction.emoji) == reactions[2] and page < pages:
                    page += 1
                    await menu.edit(embed=create_embed(page))

    @commands.group(usage='leveledroles [add|remove|clear]', aliases=['lvlrole', 'lvlroles', 'leveledrole'], case_insensitive=True)
    @commands_only()
    async def leveledroles(self, ctx):
        """Commands für die Levelrollen"""
        if ctx.invoked_subcommand is None:
            roles = list(self.con["lvlroles"].find({}).sort("level", pymongo.ASCENDING))
            if not roles:
                await ctx.send(embed=discord.Embed(
                    color=discord.Color.red(),
                    title='Keine Rollen gefunden',
                    description=f'Füge Rollen mit `{ctx.prefix}{ctx.invoked_with} add <level> <role>` hinzu'
                ))
            else:
                description = ''
                for i, entry in enumerate(roles):
                    description += f'`[{i+1}]` | <@&{entry["_id"]}> (Lvl {entry["level"]})\n'
                embed = discord.Embed(
                    color=discord.Color.blue(),
                    title=f':clipboard: Levelrollen für {ctx.guild.name}',
                    description=description
                )
                embed.set_thumbnail(url=ctx.guild.icon_url)
                await ctx.send(embed=embed)

    @leveledroles.command(usage='add <level> <role>')
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.has_permissions(administrator=True)
    async def add(self, ctx, level: int, *, role: discord.Role):
        """Fügt eine Rolle zu den Levelrollen hinzu"""
        me = ctx.guild.get_member(ctx.bot.user.id)
        if me.top_role.position < role.position:
            await ctx.send(f"{ctx.author.mention} Ich muss über der Rolle stehen, um sie vergeben zu können")
        elif level < 1:
            await ctx.send(f"{ctx.author.mention} Das Level muss mindestens 1 sein")
        else:
            self.con["lvlroles"].update({"_id": role.id}, {"$set": {"level": level}}, upsert=True)
            await ctx.send(f"Die Levelrolle {role.mention} ab Level **{level}** wurde eingefügt")

    @leveledroles.command(aliases=['delete', 'del'], usage='remove <role>')
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.has_permissions(administrator=True)
    async def remove(self, ctx, *, role: discord.Role):
        """Entfernt eine Levelrolle"""
        result = self.con["lvlroles"].find_one({"_id": role.id})
        if not result:
            await ctx.send(f"{ctx.author.mention} Ich konnte die Rolle nicht finden :/")
        else:
            self.con["lvlroles"].delete_one({"_id": role.id})
            await ctx.send(f"{ctx.author.mention} Die Levelrolle wurde erfolgreich entfernt")

    @leveledroles.command(aliases=['clean'])
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.has_permissions(administrator=True)
    async def clear(self, ctx):
        """Entfernt alle Rollen"""
        self.con["lvlroles"].delete_many({})
        await ctx.send(f"{ctx.author.mention} Alle Levelrollen wurden erfolgreich entfernt")

    @commands.command(hidden=True)
    async def setup(self, ctx):
        with open("data/reaction_roles.json", "r", encoding="utf8") as f:
            reaction_roles = json.load(f)
        f = discord.File("data/media/selfroles.png")
        msg = await ctx.send(file=f)
        for group in reaction_roles:
            embed = discord.Embed(
                color=0xff0000,
                title=group.title(),
                description=reaction_roles[group]["description"] + "\n"
                )
            for role in reaction_roles[group]["roles"]:
                embed.description += f"\n{reaction_roles[group]['roles'][role]} **{role.title()}**"
            msg = await ctx.send(embed=embed)
            for role in reaction_roles[group]["roles"]:
                await msg.add_reaction(reaction_roles[group]['roles'][role])
            
    @commands.command(hidden=True)
    async def setup_rr(self, ctx):
        with open("data/reaction_roles.json", "r", encoding="utf8") as f:
            reaction_roles = json.load(f)
        for group in reaction_roles:
            msg = await ctx.send(f"**{group.title()}**")
            for role in reaction_roles[group]["roles"]:
                await msg.edit(content=f"**{group.title()}**\nReagiere mit einem Emoji für *{role}*")
                reaction, user = await self.bot.wait_for("reaction_add", check=lambda r, u: r.message.id == msg.id)
                reaction_roles[group]["roles"][role] = str(reaction.emoji)
            with open('data/reaction_roles.json', 'w', encoding="utf8") as f:
                json.dump(reaction_roles, f, indent=4)
        await ctx.send("Fertig!")


def setup(bot):
    bot.add_cog(Ranking(bot))