import discord
from discord.ext import commands, tasks, timers
from utils.help_command import HelpCommand
from utils.utils import convert_upgrade_levels, lvlcalc
from data.auto_info import auto_info
import pymongo
import os
import json
import time
import datetime
import random
import math
import asyncio

connection = pymongo.MongoClient(os.environ.get("DB_CONNECTION"))["Dc-Server"]


def prefix_callable(bot, msg):
    user_id = bot.user.id
    return [f'<@!{user_id}> ', f'<@{user_id}> ', 'ok ']


class Bot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix=prefix_callable,
                         description="Jüngstes Gericht",
                         help_command=HelpCommand(),
                         case_insensitive=True,
                         owner_id=376100578683650048)
        self.token = os.environ.get("DISCORD_TOKEN")
        self.con = connection
        self.timer_manager = timers.TimerManager(self)
        with open("data/reaction_roles.json", "r", encoding="utf8") as f:
            self.reaction_roles = json.load(f)
        with open("data/config.json", "r") as f:
            self.config = json.load(f)
        with open("data/word_list.json") as f:
            self.word_list = json.load(f)
        for filename in os.listdir("./cogs"):
            if filename.endswith(".py"):
                self.load_extension(f"cogs.{filename[:-3]}")
        # Zwischenspeicher-Variablen
        self.last_bump = 0
        self.last_join = None
        self.fast_join_count = 0
        self.support_count = 0
        self.auto_info_page = 1
        self.rr_cd = {}
        self.last_event = 0

    def run(self):
        super().run(self.token, reconnect=True)

    async def on_ready(self):
        self.voice_xp.start()
        await self.change_presence(activity=discord.Activity(type=2, name=f"ok"), status=3)
        print("Eingeloggt als", self.user.name)

    async def on_message(self, message):
        if message.author.bot:
            if self.last_bump:
                for embed in message.embeds:
                    try:
                        if "Bump erfolgreich" in embed.description:
                            await message.channel.send(
                                f"<@{self.last_bump}>, Vielen Dank für deinen Bump! Du hast **100** :dollar: und **250** XP bekommen")
                            self.con["stats"].update_one({"_id": self.last_bump}, {
                                "$inc": {
                                    "message_xp": 250, "total_xp": 250, "balance": 100
                                }})
                    except:
                        pass
            return
        elif message.guild is None:
            return

        await bot.process_commands(message)
        ctx = await self.get_context(message)
        stats = self.con["stats"].find_one({"_id": ctx.author.id})
        afk = self.con["afk"].find_one({"_id": ctx.author.id})

        if not stats:
            self.set_standard_stats(ctx.author)

        elif int(time.time()) - stats["message_cd"] > 60:
            level, xp, cap = lvlcalc(stats["total_xp"])
            added_xp = await self.add_xp(ctx.author, exp_type="message_xp")
            if xp + added_xp >= cap:
                await message.add_reaction("⭐")
                if level:
                    await self.new_lvlrole(ctx.guild, ctx.author, ctx.channel, level=level)
            else:
                await self.add_lvlrole(ctx.guild, ctx.author, level)
        if afk:
            dif = datetime.datetime.utcnow() - afk["time"]
            if dif.total_seconds() > 15:
                await self.remove_afk_message(ctx.author, ctx.channel)
        for user in message.mentions:
            await self.check_afk(user, ctx.channel)
        if message.content.lower().startswith("!d bump"):
            self.last_bump = ctx.author.id
        if (int(time.time()) - self.last_event) > 600:
            # EVENT
            chance = random.randint(0, 100)
            if chance == 0:
                await self.guess_event(ctx.channel)
            elif chance == 1:
                await self.code_event(ctx.channel)

    async def code_event(self, channel):
        self.last_event = int(time.time())
        code = f"ok pick"
        f = discord.File("./data/media/event.gif")
        embed = discord.Embed(
            color=discord.Color.purple(),
            title="RANDOM EVENT"
        )
        embed.set_footer(text=f'Schreibe "{code}" so schnell wie möglich!')
        embed.set_image(url="attachment://event.gif")
        msg = await channel.send(file=f, embed=embed)
        while True:
            try:
                m = await self.wait_for("message", check=lambda message: message.channel.id == channel.id, timeout=20)
            except asyncio.TimeoutError:
                await msg.delete()
                return
            if m.content == code:
                await msg.delete()
                break
        self.con["stats"].update_one({"_id": m.author.id}, {
            "$inc": {
                "message_xp": 100,
                "total_xp": 100,
                "balance": 50
            }})
        await m.delete()
        await channel.send(f"{m.author.mention} hat **50** :dollar: & **100** XP bekommen!", delete_after=10)

    async def guess_event(self, channel):
        self.last_event = int(time.time())
        word = random.choice(self.word_list)
        shuffled_word = word
        while word == shuffled_word:
            foo = list(word[1:-1])
            random.shuffle(foo)
            shuffled_word = word[0] + ''.join(foo) + word[-1]
        msg = await channel.send(embed=discord.Embed(
            color=discord.Color.blurple(),
            title="Wörterraten",
            description=f"Der erste, der dieses Wort errät bekommt eine Belohnung:\n`{shuffled_word}`"
        ))
        while True:
            try:
                m = await self.wait_for("message", check=lambda message: message.channel.id == channel.id, timeout=20)
            except asyncio.TimeoutError:
                await msg.delete()
                await channel.send(embed=discord.Embed(
                    color=discord.Color.red(),
                    title="Zeit abgelaufen!",
                    description=f"Die Zeit ist abgelaufen! Die Lösung war: `{word}`"
                ), delete_after=10)
                return
            if m.content.lower() == word.lower():
                await msg.delete()
                break
        self.con["stats"].update_one({"_id": m.author.id}, {
            "$inc": {
                "message_xp": 100,
                "total_xp": 100,
                "balance": 50
            }})
        await channel.send(f"{m.author.mention} Du hast das Wort erraten und **50** :dollar: & **100** XP bekommen!", delete_after=10)
        await asyncio.sleep(10)
        await m.delete()

    def set_standard_stats(self, member):
        """Erstellt für den Member ein Profil in der Datenbank"""
        stats = {
            "_id": member.id,
            "message_xp": 0,
            "voice_xp": 0,
            "total_xp": 0,
            "balance": 0,
            "bank": 100,
            "max": 100,
            "message_cd": 0
        }
        self.con["stats"].insert_one(stats)

    def set_standard_upgrades(self, member):
        """Erstellt für den Member ein Profil für die Upgrades in der Datenbank"""
        upgrades = {
            "_id": member.id,
            "multiplier": 0,
            "money": 0,
            "crit": 0
        }
        self.con["upgrades"].insert_one(upgrades)

    async def add_xp(self, member, exp_type):
        """Gibt dem Member XP und Geld"""
        u = self.con["upgrades"].find_one({"_id": member.id})
        if not u:
            self.set_standard_upgrades(member)
        mult, money, crit = convert_upgrade_levels(u['multiplier'], u['money'], u['crit'])
        inc_exp = round(random.randint(15, 25) * mult / 100)
        inc_bal = money
        inc_bank = round(money * 2.5)
        if crit > random.randint(0, 100):
            inc_exp = inc_exp * 2
            inc_bal = inc_bal * 2
            inc_bank = inc_bank * 2
        self.con["stats"].update_one({"_id": member.id}, {
            "$set": {
                "message_cd": int(time.time())
            },
            "$inc": {
                exp_type: inc_exp,
                "total_xp": inc_exp,
                "balance": inc_bal,
                "max": inc_bank
            }})
        return inc_exp

    async def add_lvlrole(self, guild, member, level):
        """Schaut, ob der Member seine Levelrolle hat. Nützlich, wenn Jemand dem Server neu gejoint ist"""
        lvl_role = list(
            self.con["lvlroles"].find({"level": {"$lt": level + 1}}).sort("level", pymongo.DESCENDING).limit(1))
        if lvl_role:
            lvl_role = guild.get_role(lvl_role[0]["_id"])
            if lvl_role and lvl_role not in member.roles:
                await member.add_roles(lvl_role)

    async def new_lvlrole(self, guild, member, channel, level):
        """Schaut beim einem Level-up, ob der Member eine neue Levelrolle erreicht hat"""
        new_role = self.con["lvlroles"].find_one({"level": level + 1})
        if new_role:
            # Gibt die neue Rolle
            new_role = guild.get_role(new_role["_id"])
            await member.add_roles(new_role)

            # Entfernt die alte Rolle
            old_role = list(
                self.con["lvlroles"].find({"level": {"$lt": level + 1}}).sort("level", pymongo.DESCENDING).limit(
                    1))
            if old_role:
                old_role = guild.get_role(old_role[0]["_id"])
                await member.remove_roles(old_role)
            if channel:
                await channel.send(embed=discord.Embed(
                    color=new_role.color,
                    title=f"Herzlichen Glückwunsch :tada:",
                    description=f"{member.mention} Du bist jetzt {new_role.mention}!"
                ))

    async def remove_afk_message(self, member, channel):
        """Löscht die Afk-Nachricht des Members, wenn er wieder da ist"""
        self.con["afk"].delete_one({"_id": member.id})
        await channel.send(embed=discord.Embed(
            color=discord.Color.blue(),
            title='Willkommen zurück',
            description=f'{member.mention} Deine AFK-Nachricht wurde aufgehoben'),
            delete_after=3)

    async def check_afk(self, user, channel):
        """Schaut, ob der User AFK ist und sendet ggf. seine AFK-Nachricht"""
        afk = self.con["afk"].find_one({"_id": user.id})
        if afk:
            embed = discord.Embed(
                color=discord.Color.red(),
                title=f"{user} ist AFK",
                description=afk["message"],
                timestamp=afk["time"]
            )
            await channel.send(embed=embed, delete_after=8)

    @tasks.loop(minutes=1)
    async def voice_xp(self):
        for guild in self.guilds:
            for channel in guild.voice_channels:
                for member in channel.members:
                    if member.bot or member.voice.afk:
                        continue
                    stats = self.con["stats"].find_one({"_id": member.id})
                    level, xp, cap = lvlcalc(stats["total_xp"])
                    added_xp = await self.add_xp(member, exp_type="voice_xp")
                    if xp + added_xp >= cap and level:
                        await self.new_lvlrole(guild, member, None, level=level)

    async def on_member_join(self, member):
        if member.bot:
            bot_role = member.guild.get_role(self.config["bot_role"])
            await member.add_roles(bot_role)
            return

        if member.guild.verification_level == discord.VerificationLevel.high:
            await member.send(embed=discord.Embed(
                color=discord.Color.red(),
                title="Anti Raid Mode :robot:",
                description="Du wurdest vom Server entfernt, da zurzeit der **Anti Raid Mode** aktiviert ist. **Bitte versuche es in 3-4 Minuten nochmal**"
            ))
            await member.kick(reason='Anti-Raid')
            return

        joined = member.joined_at or datetime.datetime.utcnow()
        if self.last_join is None:
            self.last_join = joined

        elif (joined - self.last_join).total_seconds() <= 30:
            self.fast_join_count += 1

        if self.fast_join_count >= 5:
            await member.guild.edit(verification_level=discord.VerificationLevel.high)
            channel = member.guild.get_channel(self.config["raid_broadcast_channel"])
            message = await channel.send(embed=discord.Embed(
                color=discord.Color.red(),
                title="Raid Mode aktiviert",
                description="Auf Grund des Verdachts eines Raids ist der Server für mindestens 3 Minuten geschlossen. Die Verifizierungsstufe wurde auf hoch gestellt und neue Member werden automatisch gekickt.\n\nDiese Nachricht löscht sich automatisch, wenn der Raid Mode wieder deaktiviert ist."
            ))
            self.timer_manager.create_timer('raid_mode_expire', datetime.timedelta(minutes=3),
                                            args=(member.guild, message))

        self.last_join = joined
        stats = self.con["stats"].find_one({"_id": member.id})
        if not stats:
            self.set_standard_stats(member)
        embed = discord.Embed(
            color=0xFFDAC1,
            title=f'Hallöchen, {member.name} <:owo:681143687761494018>',
            description=f'**❥ ~ __Herzlich Willkommen auf {member.guild.name}__**:\n> ❧ ~ Wir bitten dich, die [Regeln](https://discordapp.com/channels/{member.guild.id}/{self.config["rules_channel"]}) & [Infos](https://discordapp.com/channels/{member.guild.id}/{self.config["infos_channel"]}) zu lesen.\n> ❧ ~ Vergiss nicht, dir Selfrollen zu geben & dich vorstellen.'
        )
        await member.send(embed=embed)
        await self.update_membercount(member.guild)
        gate = member.guild.get_channel(self.config["gate_channel"])
        embed = discord.Embed(color=discord.Color.green())
        embed.set_author(name=f"{member} hat den Server betreten", icon_url=member.avatar_url)
        await gate.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        await self.update_membercount(member.guild)
        gate = member.guild.get_channel(self.config["gate_channel"])
        embed = discord.Embed(color=discord.Color.red())
        embed.set_author(name=f"{member} hat den Server verlassen", icon_url=member.avatar_url)
        await gate.send(embed=embed)
        stats = self.con["stats"].find_one({"_id": member.id})
        if stats["total_xp"] < 1000:
            self.con["stats"].delete_one({"_id": member.id})
            self.con["upgrades"].delete_one({"_id": member.id})
            self.con["inventory"].delete_one({"_id": member.id})

    async def update_membercount(self, guild):
        channel = guild.get_channel(self.config["membercount_channel"])
        await channel.edit(name=f"{len(guild.members)} Mitglieder")

    async def on_raid_mode_expire(self, guild, message):
        """Wird ausgeführt, wenn der Raidmode vorbei ist"""
        await message.delete()
        await guild.edit(verification_level=discord.VerificationLevel.medium)
        self.fast_join_count = 0

    async def on_raw_reaction_add(self, payload):
        try:
            member, guild, channel, message = await self.process_payload(payload)
        except:
            return
        if guild is None:
            return
        if member.bot:
            return
        elif message.id == self.config["auto_info_message"]:
            await message.remove_reaction(payload.emoji, member)
            page = self.auto_info_page
            emoji = str(payload.emoji)
            if emoji == "⏮️" and self.auto_info_page != 1:
                page = 1
            elif emoji == "◀️" and self.auto_info_page > 1:
                page -= 1
            elif emoji == "▶️" and self.auto_info_page < len(auto_info):
                page += 1
            elif emoji == "⏭️" and self.auto_info_page != len(auto_info):
                page = len(auto_info)
            await message.edit(embed=auto_info[page-1].set_footer(text=f"Seite {page} von {len(auto_info)}"))
            self.auto_info_page = page
        if message.id == self.config["support_message"]:
            await message.remove_reaction(payload.emoji, member)
            check = discord.utils.get(guild.text_channels, topic=str(member.id))
            if check:
                await member.send(embed=discord.Embed(
                    color=discord.Color.red(),
                    title="Raum wurde nicht erstellt",
                    description="Du hast bereits einen Raum erstellt! Bitte unterlasse Spam"
                ))
            else:
                serverteam = guild.get_role(self.config["serverteam_role"])
                overwrites = {
                    guild.default_role: discord.PermissionOverwrite(read_messages=False),
                    member: discord.PermissionOverwrite(read_messages=True),
                    serverteam: discord.PermissionOverwrite(read_messages=True)
                }
                support_channel = await guild.create_text_channel(name=f"Support #{self.support_count + 1}", overwrites=overwrites)
                await support_channel.edit(topic=member.id)
                embed = discord.Embed(
                    color=discord.Color.green(),
                    title=':thumbsup: Supportraum erstellt',
                    description="In diesem Channel kannst nur du und das Serverteam schreiben. Sobald jemand bereit "
                                "ist, wird er sich um dich kümmern."
                )
                embed.set_footer(text="Klicke auf das Kreuz, um den Raum wieder zu schließen", icon_url="https://2017.igem.org/wiki/images/7/7e/T--HZAU-China--arrow.gif")
                support_message = await support_channel.send(content=member.mention, embed=embed)
                await support_message.add_reaction("❌")
                self.support_count += 1
        elif channel.topic == str(member.id) and str(payload.emoji) == "❌":
            await channel.delete()
            self.support_count -= 1
        elif channel.id == self.config["roles_channel"]:
            group = self.reaction_roles[message.embeds[0].title.lower()]
            # Check if user is on cooldown
            if group['type'] == 'single':
                if not str(member.id) in self.rr_cd:
                    self.rr_cd[str(member.id)] = int(time.time())
                elif int(time.time()) - self.rr_cd[str(member.id)] < 2:
                    await message.remove_reaction(payload.emoji, member)
                    return
                else:
                    self.rr_cd[str(member.id)] = int(time.time())
            # Remove the other reactionroles
            if group['type'] == 'single':
                for reaction in message.reactions:
                    if str(reaction.emoji) != str(payload.emoji):
                        async for user in reaction.users():
                            if user.id == member.id:
                                await reaction.remove(member)
                                other_role = self.get_role_with_emoji(group, reaction.emoji, guild)
                                await member.remove_roles(other_role)
            # Add the reactionrole
            reaction_role = self.get_role_with_emoji(group, payload.emoji, guild)
            await member.add_roles(reaction_role)

    async def on_raw_reaction_remove(self, payload):
        try:
            member, guild, channel, message = await self.process_payload(payload)
        except:
            return
        if guild is None:
            return
        if member.bot:
            return

        if channel.id == self.config["roles_channel"]:
            group = self.reaction_roles[message.embeds[0].title.lower()]
            reaction_role = self.get_role_with_emoji(group, payload.emoji, guild)
            await member.remove_roles(reaction_role)

    async def process_payload(self, payload):
        """Wandelt den Payload in ein Guild-, Member-, Channel- und Message-Object um"""
        guild = self.get_guild(payload.guild_id)
        member = guild.get_member(payload.user_id)
        channel = guild.get_channel(payload.channel_id)
        message = await channel.fetch_message(payload.message_id)
        return member, guild, channel, message

    def get_role_with_emoji(self, group, emoji, guild):
        """Sucht zu dem Emoji die passende Reactionrole"""
        name = list(group['roles'].keys())[list(group['roles'].values()).index(str(emoji))]
        role = discord.utils.get(guild.roles, name=name.title())
        return role

    async def on_voice_state_update(self, member, before, after):
        if before.channel == after.channel:
            return
        if before.channel:
            if before.channel.category_id == self.config["avc_category"] and before.channel.id != self.config["avc_channel"] and len(before.channel.members) == 0:
                await before.channel.delete()
        if after.channel:
            if after.channel.id == self.config["avc_channel"]:
                if member.bot:
                    new_channel = None
                else:
                    new_channel = await after.channel.clone(name='rename me')
                    await new_channel.edit(topic=member.id)
                await member.move_to(new_channel)

    async def on_member_update(self, before, after):
        if before.roles == after.roles:
            return
        if before.bot:
            return
        booster = discord.utils.get(before.guild.roles, name='Nitro Booster')
        if booster:
            if booster not in before.roles and booster in after.roles:
                channel = before.guild.get_channel(self.config["booster_broadcast_channel"])
                self.con["stats"].update_one({"_id": before.id}, {"$inc": {"balance": 10000}})
                embed = discord.Embed(
                    color=0xf47fff,
                    title='Vielen Dank für deinen Boost!',
                    description=f'**{before}** du hast jetzt die Möglichkeit dir eine eigene Rolle zu erstellen. Außerdem hast du **10000** :dollar: bekommen.'
                )
                await channel.send(content=before.mention, embed=embed)
            elif booster in before.roles and booster not in after.roles:
                user = self.con["booster"].find_one({"_id": before.id})
                if user:
                    role = before.guild.get_role(user["role"])
                    if role:
                        await role.delete()

    async def oon_command_error(self, ctx, error):
        if isinstance(error, commands.CommandNotFound):
            return
        elif isinstance(error, commands.CheckFailure):
            await ctx.message.add_reaction("⛔")
            return
        elif isinstance(error, commands.CommandOnCooldown):
            retry_after = round(error.retry_after, 1)

            if retry_after > 60:
                minutes, seconds = divmod(retry_after, 60)
                minutes = math.floor(minutes)
                seconds = math.floor(seconds)
                n, s = 'n', 'n'
                if minutes == 1:
                    n = ''
                if seconds == 1:
                    s = ''
                description = f'Bitte warte noch `{minutes}` Minute{n} und `{seconds}` Sekunde{s}'

            else:
                s = 'n'
                if retry_after == 1:
                    s = ''
                description = f'Bitte warte noch `{retry_after}` Sekunde{s}'

            await ctx.send(embed=discord.Embed(
                color=discord.Color.red(),
                title='Cooldown',
                description=description
            ))
        elif isinstance(error, commands.MissingPermissions):
            perms = ''
            for perm in error.missing_perms:
                perms += f'`{perm}`, '
            await ctx.send(embed=discord.Embed(
                color=discord.Color.red(),
                title='Keine Berechtigung',
                description=f'Du brauchst folgende Berechtigung, um den Command ausführen zu können: {perms[:-2]}'
            ))
        elif isinstance(error, commands.BotMissingPermissions):
            perms = ''
            for perm in error.missing_perms:
                perms += f'`{perm}`, '
            await ctx.send(embed=discord.Embed(
                color=discord.Color.red(),
                title='Fehlende Berechtigung',
                description=f'Der Bot braucht folgende Berechtigung, um den Command ausführen zu können: {perms[:-2]}'
            ))
        elif isinstance(error, commands.BadArgument):
            await ctx.send(embed=discord.Embed(
                color=discord.Color.red(),
                title='Falsches Format',
                description=str(error)
            ))
        elif isinstance(error, commands.MissingRequiredArgument):
            usage = ctx.command.usage
            if not usage:
                usage = ctx.command.name
            await ctx.send(embed=discord.Embed(
                color=discord.Color.red(),
                title='Fehlendes Argument',
                description=f'Verwendung: `{usage}`\nDas folgende Argument fehlt: `{error.param}`'
            ))
        elif isinstance(error, commands.MissingRole):
            await ctx.send(embed=discord.Embed(
                color=discord.Color.red(),
                title='Keine Berechtigung',
                description=f'Nur User mit der Rolle **{error.missing_role}** können diesen Command benutzen'
            ))
        elif isinstance(error, commands.MissingAnyRole):
            roles = '**, **'.join(error.missing_roles)
            await ctx.send(embed=discord.Embed(
                color=discord.Color.red(),
                title='Keine Berechtigung',
                description=f'Nur User mit den Rollen **{roles}** können diesen Command benutzen'
            ))
        else:
            await ctx.send(embed=discord.Embed(
                color=discord.Color.red(),
                title='Command-Error',
                description=str(error)
            ))


if __name__ == '__main__':
    bot = Bot()
    bot.run()
