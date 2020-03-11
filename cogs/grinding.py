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
        with open("data/crafting.json", "r", encoding="UTF-8") as f:
            self.recipes = json.load(f)

    @commands.command(usage="craft <item>", aliases=["crafting"])
    @commands_only()
    async def craft(self, ctx, *, item: str = None):
        """Carfting-Commands"""
        inv = self.con["inventory"].find_one({"_id": ctx.author.id})
        items = self.con["items"].find()
        tools = list(self.con["tools"].find())
        emojis = {item["_id"]: item["emoji"] for item in list(items) + tools}
        tools = [t["_id"] for t in tools]
        if not item:
            page = 0
            pages, b = divmod(len(self.recipes), 5)
            if b != 0:
                pages += 1

            def create_embed(p):
                embed = discord.Embed(
                    color=discord.Color.blue(),
                    title=f"Crafting ({p+1}/{pages})",
                    description=f"Benutze `{ctx.prefix}craft <item>`, um ein Item zu craften.\n"
                )
                for crafting_item, ingredients in [(a, b) for a, b in self.recipes.items()][p * 5:p * 5 + 5]:
                    lines, remainer = divmod(len(ingredients), 5)
                    if remainer != 0:
                        lines += 1
                    recipe = ""
                    for i in range(lines):
                        ing = []
                        for ingredient, count in list(ingredients.items())[i * 5:i * 5 + 5]:
                            if ingredient in tools:
                                continue
                            ing.append(f"{count}x {emojis[ingredient]}")
                        recipe += "\n> " + " ".join(ing)
                    embed.description += f"\n**» {emojis[crafting_item]} __{crafting_item.title()}__**:{recipe}"
                return embed

            menu = await ctx.send(embed=create_embed(page))
            if pages > 1:
                reactions = ['◀', '▶']
                for reaction in reactions:
                    await menu.add_reaction(reaction)
                while True:
                    try:
                        reaction, user = await ctx.bot.wait_for("reaction_add", check=lambda r, u: r.message.id == menu.id and u == ctx.author and str(r.emoji) in reactions, timeout=60)
                    except asyncio.TimeoutError:
                        await menu.clear_reactions()
                        return
                    await menu.remove_reaction(reaction, user)
                    if str(reaction.emoji) == reactions[0] and page > 0:
                        page -= 1
                    elif str(reaction.emoji) == reactions[1] and page < pages-1:
                        page += 1
                    await menu.edit(embed=create_embed(page))
        elif item.lower() in self.recipes:
            recipe = self.recipes[item.lower()]
            embed = discord.Embed(
                color=discord.Color.green(),
                title=item.title(),
                description=""
            )
            missing = False
            for ingredient, count in recipe.items():
                amount = inv.get(ingredient, 0)
                if amount >= count:
                    amount = count
                else:
                    missing = True
                embed.description += f"\n> **{amount}/{count}** {ingredient} {emojis[ingredient]}"
            if missing:
                embed.color = discord.Color.red()
                await ctx.send(embed=embed)
            else:
                msg = await ctx.send(embed=embed)
                await msg.add_reaction("☑️")
                try:
                    reaction, user = await ctx.bot.wait_for("reaction_add", check=lambda r, u: r.message.id == msg.id and u == ctx.author and str(r.emoji) == "☑️", timeout=60)
                except asyncio.TimeoutError:
                    await msg.clear_reactions()
                    return
        else:
            await ctx.send(f"{ctx.author.mention} Ich konnte dieses Item nicht finden.")

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
