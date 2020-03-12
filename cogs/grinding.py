import discord
from discord.ext import commands
from main import connection
from utils.checks import commands_only
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
    async def craft(self, ctx, *, args: str = None):
        """Carfting-Commands"""
        inv = self.con["inventory"].find_one({"_id": ctx.author.id})
        items = self.con["items"].find()
        tools = list(self.con["tools"].find())
        emojis = {item["_id"]: item["emoji"] for item in list(items) + tools}
        tools = [t["_id"] for t in tools]
        if not args:
            page = 0
            pages = len(self.recipes)

            def create_embed(p):
                group = list(self.recipes)[p]
                embed = discord.Embed(
                    color=discord.Color.blue(),
                    title=f"{group.title()} ({p+1}/{pages})",
                    description=f"Benutze `{ctx.prefix}craft item`, um ein Item zu craften.\nWenn du mehrere Items auf einmal craften möchtest, benutze `{ctx.prefix}craft item=3`\n"
                )
                for crafting_item, ingredients in [(a, b) for a, b in self.recipes[group].items()]:
                    copy = [k for k in ingredients.keys()]
                    for ingredient in copy:
                        if ingredient in tools:
                            ingredients.pop(ingredient)
                    lines, remainer = divmod(len(ingredients), 5)
                    if remainer != 0:
                        lines += 1
                    recipe = ""
                    for i in range(lines):
                        ing = []
                        for ingredient, count in list(ingredients.items())[i * 5:i * 5 + 5]:
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
        else:
            recipes = {}
            for group in self.recipes.values():
                for name, recipe in group.items():
                    recipes[name] = recipe
            args = args.split("=")
            if len(args) == 1:
                args.append(1)
            elif len(args) != 2:
                await ctx.send(f"{ctx.author.mention} Wenn du mehrere Items auf einmal craften möchtest, benutze `{ctx.prefix}craft item=3`")
                return
            item = args[0]
            amount = int(args[1])
            if item.lower() in recipes:
                recipe = recipes[item.lower()]
                embed = discord.Embed(
                    color=discord.Color.green(),
                    title=item.title(),
                    description=""
                )
                missing = False
                inc = {}
                unset = {}
                for ingredient, count in recipe.items():
                    count = count * amount
                    inv_count = inv.get(ingredient, 0)
                    if inv_count > count:
                        inv_count = count
                        inc[ingredient] = -count
                    elif count == inv_count:
                        unset[ingredient] = 1
                    else:
                        missing = True
                    embed.description += f"\n> **{inv_count}/{count}** {ingredient} {emojis[ingredient]}"
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
                    inc[item.lower()] = amount
                    if unset:
                        self.con["inventory"].update({"_id": ctx.author.id}, {"$inc": inc, "$unset": unset}, upsert=True)
                    else:
                        self.con["inventory"].update({"_id": ctx.author.id}, {"$inc": inc   }, upsert=True)
                    await msg.edit(embed=discord.Embed(
                        color=discord.Color.green(),
                        title="Crafting erfolgreich!",
                        description=f"{ctx.author.mention} Du hast {amount}x **{item.title()}** {emojis[item.lower()]} gecraftet!"
                    ))
            else:
                await ctx.send(f"{ctx.author.mention} Ich konnte dieses Item nicht finden.")

    @commands.command()
    @commands.cooldown(1, 300, commands.BucketType.user)
    @commands_only()
    async def mine(self, ctx):
        """Baue Resourcen ab und bekomme Items"""
        pickaxes = ["infinity spitzhacke", "neutron spitzhacke", "komet spitzhacke", "stern spitzhacke", "pauls spitzhacke"]
        inv = self.con["inventory"].find_one({"_id": ctx.author.id})
        for pickaxe in pickaxes:
            if pickaxe in inv:
                break
        else:
            await ctx.send(f"{ctx.author.mention} Du brauchst eine Spitzhacke, um diesen Command verwenden zu können. Siehe `{ctx.prefix}shop` & `{ctx.prefix}craft`")
            return
        items = list(self.con["items"].find())
        tools = list(self.con["tools"].find())
        emojis = {item["_id"]: item["emoji"] for item in items + tools}
        tool = self.con["mine-drops"].find_one({"_id": pickaxe})
        cash = tool["cash"].split("-")
        cash = random.randint(int(cash[0]), int(cash[1]))
        drops = tool["items"].split("-")
        drops = random.randint(int(drops[0]), int(drops[1]))
        embed = discord.Embed(
            color = discord.Color.green(),
            title=f"{emojis[pickaxe]} ***Du hast ein paar Items abgebaut!*** ({pickaxe.title()})",
            description=f"> +{cash} **Dollar** :dollar:"
        )
        rewards = numpy.random.choice(list(tool["props"].keys()), drops, p=list(tool["props"].values()))
        loot = {}
        for reward in rewards:
            loot[reward] = loot.get(reward, 0) + 1
        for item, count in loot.items():
            embed.description += f"\n> {count}x **{item.title()}** {emojis[item]}"
        if random.random() < tool["break"]:
            embed.description += f"\n:worried: **Beim Abbauen ist deine Spitzhacke kaputt gegangen!** ({int(tool['break']*100)}% Chance)"
            remove_item(ctx.author, pickaxe, 1)
        self.con["stats"].update({"_id": ctx.author.id}, {"$inc": {"balance": cash}})
        self.con["inventory"].update({"_id": ctx.author.id}, {"$inc": loot}, upsert=True)
        await ctx.send(embed=embed)

    @commands.command()
    @commands.cooldown(1, 300, commands.BucketType.user)
    @commands_only()
    async def fish(self, ctx):
        """Fische nach Resourcen und bekomme Items"""
        fishing_rods = ["infinity angel", "neutron angel", "komet angel", "stern angel", "zanas angel"]
        inv = self.con["inventory"].find_one({"_id": ctx.author.id})
        for fishing_rod in fishing_rods:
            if fishing_rod in inv:
                break
        else:
            await ctx.send(f"{ctx.author.mention} Du brauchst eine Angel, um diesen Command verwenden zu können. Siehe `{ctx.prefix}shop` & `{ctx.prefix}craft`")
            return
        items = list(self.con["items"].find())
        tools = list(self.con["tools"].find())
        emojis = {item["_id"]: item["emoji"] for item in items + tools}
        tool = self.con["fish-drops"].find_one({"_id": fishing_rod})
        cash = tool["cash"].split("-")
        cash = random.randint(int(cash[0]), int(cash[1]))
        drops = tool["items"].split("-")
        drops = random.randint(int(drops[0]), int(drops[1]))
        embed = discord.Embed(
            color = discord.Color.green(),
            title=f"{emojis[fishing_rod]} ***Du hast nach Items gefischt!*** ({fishing_rod.title()})",
            description=f"> +{cash} **Dollar** :dollar:"
        )
        rewards = numpy.random.choice(list(tool["props"].keys()), drops, p=list(tool["props"].values()))
        loot = {}
        for reward in rewards:
            loot[reward] = loot.get(reward, 0) + 1
        for item, count in loot.items():
            embed.description += f"\n> {count}x **{item.title()}** {emojis[item]}"
        if random.random() < tool["break"]:
            embed.description += f"\n:worried: **Beim Abbauen ist deine Angel kaputt gegangen!** ({int(tool['break']*100)}% Chance)"
            remove_item(ctx.author, fishing_rod, 1)
        self.con["stats"].update({"_id": ctx.author.id}, {"$inc": {"balance": cash}})
        self.con["inventory"].update({"_id": ctx.author.id}, {"$inc": loot}, upsert=True)
        await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(Grinding(bot))
