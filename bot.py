import discord
from discord.ext import commands
from flask import Flask
import threading
import os
import random
import asyncio

# =======================
# KEEP ALIVE (Render)
# =======================

app = Flask('')

@app.route('/')
def home():
    return "Bot is alive!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = threading.Thread(target=run)
    t.start()

# =======================
# BOT SETUP
# =======================

intents = discord.Intents.default()
intents.message_content = True
intents.reactions = True
intents.members = True

bot = commands.Bot(
    command_prefix="!",
    intents=intents,
    help_command=None
)

# =======================
# DATA STORAGE
# =======================

coins = {}
work_cooldown = {}
daily_cooldown = {}

# =======================
# EVENTS
# =======================

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

# =======================
# HELP COMMAND
# =======================

@bot.command()
async def help(ctx):
    embed = discord.Embed(
        title="📜 Bot Commands",
        description="Here are the available commands:",
        color=discord.Color.purple()
    )

    embed.add_field(name="💼 !work", value="Earn coins (30s cooldown)", inline=False)
    embed.add_field(name="🎁 !daily", value="Claim daily reward (24h cooldown)", inline=False)
    embed.add_field(name="💰 !balance", value="Check your coins", inline=False)
    embed.add_field(name="🃏 !cards", value="View your cards", inline=False)

    await ctx.send(embed=embed)

# =======================
# BALANCE
# =======================

@bot.command()
async def balance(ctx):
    user = ctx.author.id
    amount = coins.get(user, 0)
    await ctx.send(f"💰 You have {amount} coins.")

# =======================
# WORK COMMAND
# =======================

@bot.command()
async def work(ctx):
    user_id = str(ctx.author.id)

    if user_id not in data["players"]:
        await ctx.send("Use `!start` first 💜")
        return

    now = asyncio.get_event_loop().time()

    if user_id in work_cooldown:
        if work_cooldown[user_id] > now:
            remaining = int(work_cooldown[user_id] - now)
            await ctx.send(f"⏳ Wait {remaining}s before working again.")
            return

    # 💰 Coins
    earned = random.randint(50, 150)
    data["players"][user_id]["coins"] += earned

    # 🎴 Random Card Drop
    member = random.choice(list(data["cards"].keys()))
    rarity = random.choice(list(data["cards"][member].keys()))

    card_info = data["cards"][member][rarity]
    card_name = f"{card_info['name']} ({rarity}★)"

    data["players"][user_id]["cards"].append(card_name)

    # Save
    save_data(data)

    work_cooldown[user_id] = now + 30

    embed = discord.Embed(
        title="💼 You worked!",
        description=f"💰 +{earned} coins\n🃏 You received: **{card_name}**",
        color=discord.Color.purple()
    )

    embed.set_image(url=card_info["image"])

    await ctx.send(embed=embed)

# =======================
# DAILY COMMAND
# =======================

@bot.command()
async def daily(ctx):
    user_id = str(ctx.author.id)

    if user_id not in data["players"]:
        await ctx.send("Use `!start` first 💜")
        return

    now = asyncio.get_event_loop().time()

    if user_id in daily_cooldown:
        if daily_cooldown[user_id] > now:
            remaining = int(daily_cooldown[user_id] - now)
            hours = remaining // 3600
            minutes = (remaining % 3600) // 60
            await ctx.send(f"⏳ Come back in {hours}h {minutes}m.")
            return

    # 💰 Coins
    reward = 500
    data["players"][user_id]["coins"] += reward

    # 🎴 Random Card Drop
    member = random.choice(list(data["cards"].keys()))
    rarity = random.choice(list(data["cards"][member].keys()))

    card_info = data["cards"][member][rarity]
    card_name = f"{card_info['name']} ({rarity}★)"

    data["players"][user_id]["cards"].append(card_name)

    # Save
    save_data(data)

    daily_cooldown[user_id] = now + 86400

    embed = discord.Embed(
        title="🎁 Daily Reward!",
        description=f"💰 +{reward} coins\n🃏 You received: **{card_name}**",
        color=discord.Color.purple()
    )

    embed.set_image(url=card_info["image"])

    await ctx.send(embed=embed)

# =======================
# CARD REACTION MENU
# =======================

@bot.command()
async def mycards(ctx):
    user_id = str(ctx.author.id)

    if user_id not in data["players"]:
        await ctx.send("Use `!start` first 💜")
        return

    cards = data["players"][user_id]["cards"]

    if not cards:
        await ctx.send("You have no cards yet 💜")
        return

    current_page = 0

    def create_embed(index):
        card_string = cards[index]

        # Extract member name (first word)
        member = card_string.split(" ")[0]

        # Extract rarity number inside parentheses
        rarity = card_string.split("(")[1].split("★")[0]

        card_data = data["cards"].get(member, {}).get(rarity)

        embed = discord.Embed(
            title=f"🃏 {card_string}",
            color=discord.Color.purple()
        )

        if card_data:
            embed.set_image(url=card_data["image"])

        embed.set_footer(text=f"Card {index+1}/{len(cards)}")

        return embed

    message = await ctx.send(embed=create_embed(current_page))

    if len(cards) == 1:
        return

    await message.add_reaction("⬅️")
    await message.add_reaction("➡️")

    def check(reaction, user):
        return (
            user == ctx.author and
            str(reaction.emoji) in ["⬅️", "➡️"] and
            reaction.message.id == message.id
        )

    while True:
        try:
            reaction, user = await bot.wait_for("reaction_add", timeout=120, check=check)

            if str(reaction.emoji) == "➡️":
                current_page = (current_page + 1) % len(cards)
            else:
                current_page = (current_page - 1) % len(cards)

            await message.edit(embed=create_embed(current_page))
            await message.remove_reaction(reaction, user)

        except asyncio.TimeoutError:
            break

# =======================
# RUN BOT
# =======================

if __name__ == "__main__":
    keep_alive()
    TOKEN = os.environ.get("DISCORD_TOKEN")
    bot.run(TOKEN)


