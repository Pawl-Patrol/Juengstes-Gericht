import discord
from discord.ext import commands
from main import connection
from utils.checks import casino_only
from utils.converters import bet
import json
import random
import asyncio
import math


class Gambling(commands.Cog, command_attrs=dict(cooldown_after_parsing=True)):

    def __init__(self, bot):
        self.emoji = ":game_die:"
        self.bot = bot
        self.con = connection
        with open("data/gambling.json", "r") as f:
            self.gambling = json.load(f)
        self.slots_emojis = self.gambling["slots_emojis"]
        self.blackjack_cards = self.gambling["blackjack_cards"]
        self.blackjack_reactions = self.gambling["blackjack_reactions"]

    # noinspection PyTypeChecker,PyUnresolvedReferences,PyDunderSlots
    @commands.command(usage='slots <bet>', aliases=['slot'])
    @commands.cooldown(1, 7, commands.BucketType.user)
    @casino_only()
    async def slots(self, ctx, amount: bet):
        """Bentuzt die Slotmaschine"""
        self.con["stats"].update({"_id": ctx.author.id}, {"$inc": {"balance": -amount}})
        choices = [':bell:', ':game_die:', ':four_leaf_clover:', ':gem:']
        emojis = self.slots_emojis.copy()
        random.shuffle(emojis)

        def slots_embed():
            field = emojis[0] + ' | ' + emojis[1] + ' | ' + emojis[2] + '\n' + emojis[3] + ' | ' + emojis[
                4] + ' | ' + \
                    emojis[5] + '\n' + emojis[6] + ' | ' + emojis[7] + ' | ' + emojis[8]
            cembed = discord.Embed(
                color=discord.Color.blurple(),
                description=f'─:slot_machine: **| Slots**─\n{field}\n─:slot_machine: **| Slots**─'
            )
            return cembed

        msg = await ctx.send(embed=slots_embed())
        for i in range(3):
            await asyncio.sleep(1.5)
            emojis[i] = random.choice(choices)
            emojis[i + 3] = random.choice(choices)
            emojis[i + 6] = random.choice(choices)
            await msg.edit(embed=slots_embed())
        profit = 0
        if emojis[0] == emojis[1] and emojis[0] == emojis[2]:
            profit += amount * 2
        if emojis[3] == emojis[4] and emojis[3] == emojis[5]:
            profit += amount * 2
        if emojis[6] == emojis[7] and emojis[6] == emojis[8]:
            profit += amount * 2
        if emojis[0] == emojis[3] and emojis[0] == emojis[6]:
            profit += amount * 2
        if emojis[1] == emojis[4] and emojis[1] == emojis[7]:
            profit += amount * 2
        if emojis[2] == emojis[5] and emojis[2] == emojis[8]:
            profit += amount * 2
        if emojis[0] == emojis[4] and emojis[0] == emojis[8]:
            profit += amount * 2
        if emojis[6] == emojis[4] and emojis[6] == emojis[2]:
            profit += amount * 2
        embed = slots_embed()
        v = '+' if profit != 0 else ''
        embed.description = embed.description + f'\n**{v}{profit - amount}** :dollar:'
        if profit != 0:
            embed.color = discord.Color.green()
            self.con["stats"].update({"_id": ctx.author.id}, {"$inc": {"balance": profit}})
        else:
            embed.color = discord.Color.red()
        await msg.edit(embed=embed)

    @commands.command(usage='blackjack <bet>', aliases=['bj'])
    @commands.cooldown(1, 10, commands.BucketType.user)
    @casino_only()
    async def blackjack(self, ctx, amount: bet):
        """Spiele Blackjack gegen den Bot"""
        self.con["stats"].update({"_id": ctx.author.id}, {"$inc": {"balance": -amount}})
        bal = self.con["stats"].find_one({"_id": ctx.author.id}, {"balance": 1})["balance"]
        double = True if bal - amount >= 0 else False
        player = []
        comp = []

        def new(deck):
            card = random.choice(list(self.blackjack_cards))
            deck.append(card)

        def total(deck):
            hand = []
            for card in deck:
                hand.append(self.blackjack_cards[card])
            value = sum(hand)
            aces = hand.count(11)
            if value > 21 and aces > 0:
                while aces > 0 and value > 21:
                    value -= 10
                    aces -= 1
            return value

        def show():
            cembed = discord.Embed(
                color=0x1,
                title=':black_joker: Blackjack'
            )
            r = self.blackjack_reactions
            if playing:
                desc = f":dollar: Bet: **{amount}**\n{r['hit']} Karte ziehen\n{r['stand']} Meine Karten aufdecken\n{r['fold']} Aufgeben und die Hälfte zurückerhalten"
                if double:
                    desc += f"\n{r['double']} Karte ziehen & Einsatz verdoppeln"
                cembed.description = desc
                cembed.set_footer(text="Du hast 60 Sekunden Zeit")
            cembed.add_field(name=f"Deine Karten ({player_total})", value=' '.join(player), inline=True)
            cembed.add_field(name=f"Meine Karten ({comp_total})", value=f'{comp[0]} <:NONE:664113279806996508>',
                             inline=True)
            return cembed

        new(player)
        new(player)
        new(comp)
        new(comp)
        player_total = total(player)
        comp_total = f"{self.blackjack_cards[comp[0]]} + ?"

        playing = True
        msg = None
        if player_total == 21:
            playing = False
            msg = await ctx.send(":tada:")
        else:
            msg = await ctx.send(embed=show())
            for reaction in self.blackjack_reactions:
                await msg.add_reaction(self.blackjack_reactions[reaction])

        while playing:

            try:
                reaction, user = await ctx.bot.wait_for("reaction_add", check=lambda r, u: r.message.id == msg.id and u.id == ctx.author.id,
                                                        timeout=60)
            except asyncio.TimeoutError:
                await msg.edit(embed=discord.Embed(title=":black_joker: Blackjack", colour=discord.Colour(0x1),
                                                   description='Du hast nicht geantwortet und das Spiel ist vorbei!'))
                return
            await msg.remove_reaction(reaction, user)

            if str(reaction.emoji) == self.blackjack_reactions['hit']:
                new(player)
                double = False
                await msg.remove_reaction(self.blackjack_reactions['double'], ctx.bot.user)

            elif str(reaction.emoji) == self.blackjack_reactions['stand']:
                playing = False

            elif str(reaction.emoji) == self.blackjack_reactions['double'] and double:
                new(player)
                self.con["stats"].update({"_id": ctx.author.id}, {"$inc": {"balance": -amount}})
                amount = amount * 2
                playing = False

            elif str(reaction.emoji) == self.blackjack_reactions['fold']:
                playing = False
                self.con["stats"].update({"_id": ctx.author.id}, {"$inc": {"balance": math.floor(amount / 2)}})
                embed = show()
                embed.description = 'Du hast aufgegeben!'
                await msg.edit(embed=embed)
                return

            player_total = total(player)
            if player_total > 20:
                playing = False
            if playing:
                await msg.edit(embed=show())

        while total(comp) < 18:
            new(comp)
        comp_total = total(comp)

        embed = show()

        if player_total == 21 and comp_total != 21:
            embed.description = f'Du hast **{amount * 2}** :dollar: gewonnen!'
            await msg.edit(embed=embed)
            self.con["stats"].update({"_id": ctx.author.id}, {"$inc": {"balance": amount * 3}})
            return

        elif player_total > 21:
            embed.description = f'Du hast **{amount}** :dollar: verloren!'

        elif comp_total > 21:
            embed.description = f'Du hast **{amount}** :dollar: gewonnen!'
            self.con["stats"].update({"_id": ctx.author.id}, {"$inc": {"balance": amount * 2}})

        elif player_total < comp_total:
            embed.description = f'Du hast **{amount}** :dollar: verloren!'

        elif player_total == comp_total:
            embed.description = 'Unentschieden!'
            self.con["stats"].update({"_id": ctx.author.id}, {"$inc": {"balance": amount}})

        else:
            embed.description = f'Du hast **{amount}** :dollar: gewonnen!'
            self.con["stats"].update({"_id": ctx.author.id}, {"$inc": {"balance": amount * 2}})

        embed.set_field_at(1, name=f"Meine Karten ({comp_total})", value=' '.join(comp), inline=True)
        await msg.edit(embed=embed)

    @commands.command(aliases=["jp"])
    @commands.cooldown(1, 80, commands.BucketType.guild)
    async def jackpot(self, ctx):
        """Startet einen Jackpot"""
        embed = discord.Embed(color=0xC8B115, title=':moneybag: Jackpot ─ 0 Dollar', description='Benutze `ok join <Einsatz>`, um teilzunehmen')
        embed.set_footer(text='60 Sekunden übrig')
        msg = await ctx.send(embed=embed)
        price = 0
        jackpot = {}
        def sortsec(val):
            return val[1]
        while True:
            try:
                message = await self.bot.wait_for('message', check=lambda message: message.content.lower().startswith('ok join') and message.guild.id == ctx.guild.id,  timeout=30)
            except asyncio.TimeoutError:
                break
            content = message.content.lower().replace('ok join ', '')
            if not content.isdigit() and not content in ['all', 'max']:
                await ctx.send(f'{message.author.mention} Nutze: `ok join [Einsatz]`')
            else:
                bal = self.con["stats"].find_one({"_id": message.author.id}, {"balance": 1})["balance"]
                if content in ['max', 'all']:
                    bet = bal
                elif int(content) > bal:
                    await ctx.send(f'{message.author.mention} Du hast nicht genügend Bargeld :(')
                    continue
                else:
                    bet = int(content)
                key = str(message.author.id)
                jackpot[key] = jackpot.get(key, 0) + bet
                price += bet
                self.con["stats"].update({"_id": ctx.author.id}, {"$inc": {"balance": -bet}})
                embed=discord.Embed(color=0xC8B115, title=f':moneybag: Jackpot ─ {price} Dollar', description='Benutze `ok join <Einsatz>`, um teilzunehmen\n')
                embed.set_footer(text='60 seconds left')
                for user, bet in sorted(jackpot.items(), key=lambda item: item[1], reverse=True):
                    embed.description += f"\n<@{user}> ─ **{round((bet/price)*100)}%** ({bet} Dollar)"
                await message.delete()
                await msg.edit(embed=embed)
        if price == 0:
            ctx.send(embed=discord.Embed(color=0xC8B115, title=':moneybag: Jackpot ─ 0 Dollar', description='Jackpot wurde abgebrochen, da sich nicht genug Leute gefunden haben'))
        else:
            randint = random.randint(1, price)
            for user, bet in sorted(jackpot.items(), key=lambda item: item[1]):
                winner = user
                if randint <= bet:
                    break
            await msg.edit(embed=discord.Embed(color=0xC8B115, title=':moneybag: Jackpot ─ GEWINNER', description=f'<@{winner}> hat den Jackpot geknackt! **+{price} :dollar:**'))
            self.con["stats"].update({"_id": winner}, {"$inc": {"balance": price}})

def setup(bot):
    bot.add_cog(Gambling(bot))
