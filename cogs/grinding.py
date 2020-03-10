import discord
from discord.ext import commands
from main import connection
from utils.checks import commands_only, has_any_item
from cogs.economy import remove_item
import random
import numpy
import json
import asyncio


class Grinding(commands.Cog, command_attrs=dict(cooldown_after_parsing=True)):

    def __init__(self, bot):
        self.bot = bot
        self.con = connection
        with open("data/crafting.json", "r") as f:
            self.recipes = json.load(f)

    @commands.command(usage="craft <item>", aliases=["crafting"])
    @commands_only()
    async def craft(self, ctx, page: int = 1):
        """Carfting-Commands"""
        inv = self.con["inventory"].find_one({"_id": ctx.author.id})
        items = list(self.con["items"].find())
        emojis = {item["_id"]: item["emoji"] for item in items}
        pages = len(self.recipes)
        if page < 1:
            page = 1
        elif page > pages:
            page = pages

        def create_embed(page):
            item = list(self.recipes.keys())[page-1]
            ingredients = self.recipes[item]
            embed = discord.Embed(
                color=discord.Color.green(),
                title=f"{emojis[item]} {item.title()} ({page}/{len(self.recipes)})",
                description=f"❥ ~ `{ctx.prefix}craft {item}`"
            )
            missing = False
            for ingredient, count in ingredients.items():
                amount = inv.get(ingredient, 0)
                embed.description += f"\n> **{amount}/{count}** {ingredient.title()} {emojis[ingredient]}"
                if amount < count:
                    missing = True
            if missing:
                embed.color = discord.Color.red()
            return embed, missing

        embed, missing = create_embed(page)
        menu = await ctx.send(embed=embed)
        if pages > 1:
            reactions = ['◀', '☑️', '▶']
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
                elif str(reaction.emoji) == reactions[1] and not missing:
                    await menu.delete()
                    item = list(self.recipes.keys())[page-1]
                    post = {k: -v for k, v in self.recipes[item].items()}
                    post[item] = 1
                    self.con["inventory"].update({"_id": ctx.author.id}, {"$inc": post}, upsert=True)
                    await ctx.send(f"{ctx.author.mention} Du hast **1x {item.title()} {emojis[item.lower()]}** gecraftet!")
                    return
                elif str(reaction.emoji) == reactions[2] and page < pages:
                    page += 1
                embed, missing = create_embed(page)
                await menu.edit(embed=embed)

    @commands.command()
    @commands.cooldown(1, 300, commands.BucketType.user)
    @commands_only()
    @has_any_item(["spitzhacke", "ungewöhnliche spitzhacke", "seltene spitzhacke", "legendäre spitzhacke", "infiniy spitzhacke"])
    async def mine(self, ctx):
        """Baue Resourcen ab und bekomme Items"""
        pickaxes = {
            "infinity spitzhacke": 5,
            "legendäre spitzhacke": 4,
            "seltene spitzhacke": 3,
            "ungewöhnliche spitzhacke": 2,
            "spitzhacke": 1
        }
        items = list(self.con["items"].find())
        emojis = {item["_id"]: item["emoji"] for item in items}
        inv = self.con["inventory"].find_one({"_id": ctx.author.id})
        for pickaxe, mult in pickaxes.items():
            if pickaxe in inv:
                break
        cash = random.randint(5*mult, 5*mult)
        embed = discord.Embed(
            color = discord.Color.green(),
            title=f"***Du hast Mineralien abgebaut***",
            description = f"> +{cash} **Dollar** :dollar:"
        )
        loot = self.get_random_items(times=mult)
        for item, count in loot.items():
            embed.description += f"\n> {count}x **{item.title()}** {emojis[item]}"
        if random.randint(0, 8*mult*mult) == 0:
            embed.description += "\n:worried: **Beim Abbauen ist deine Spitzhacke kaputt gegangen!**"
            remove_item(ctx.author, pickaxe, 1)
        await ctx.send(embed=embed)
        self.con["stats"].update({"_id": ctx.author.id}, {"$inc": {"balance": cash}})
        self.con["inventory"].update({"_id": ctx.author.id}, {"$inc": loot}, upsert=True)

    @commands.command()
    @commands.cooldown(1, 300, commands.BucketType.user)
    @commands_only()
    @has_any_item(["angel", "ungewöhnliche angel", "seltene angel", "legendäre angel", "infinity angel"])
    async def fish(self, ctx):
        """Fische nach Resourcen"""
        rods = {
            "infinity angel": 5,
            "legendäre angel": 4,
            "seltene angel": 3,
            "ungewöhnliche angel": 2,
            "angel": 1
        }
        items = list(self.con["items"].find())
        emojis = {item["_id"]: item["emoji"] for item in items}
        inv = self.con["inventory"].find_one({"_id": ctx.author.id})
        for rod, mult in rods.items():
            if rod in inv:
                break
        cash = random.randint(15*mult, 25*mult)
        embed = discord.Embed(
            color = discord.Color.green(),
            title=f"***Du hast ein paar Items gefischt***",
            description = f"> +{cash} **Dollar** :dollar:"
        )
        loot = self.get_random_items(times=mult)
        for item, count in loot.items():
            embed.description += f"\n> {count}x **{item.title()}** {emojis[item]}"
        if random.randint(0, 8*mult) == 0:
            embed.description += "\n:worried: **Beim Angeln ist deine Angel kaputt gegangen!**"
            remove_item(ctx.author, rod, 1)
        await ctx.send(embed=embed)
        self.con["stats"].update({"_id": ctx.author.id}, {"$inc": {"balance": cash}})
        self.con["inventory"].update({"_id": ctx.author.id}, {"$inc": loot}, upsert=True)

    def get_random_items(self, times):
        drops = {
            "neutron nugget": 0.02,
            "komet": 0.03,
            "edelstein": 0.05,
            "sternenstaub": 0.07,
            "juwelfragment": 0.13,
            "kleeblatt": 0.2,
            "spinnwebe": 0.2,
            "ziegelstein": 0.3,
        }
        loot = {}
        rewards = numpy.random.choice(list(drops.keys()), random.randint(1*times, 3*times), p=list(drops.values()))
        for reward in rewards:
            loot[reward] = loot.get(reward, 0) + 1
        return loot


def setup(bot):
    bot.add_cog(Grinding(bot))