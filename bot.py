import discord
from discord.ext import commands
from flask import Flask
import threading
import os
import random
import asyncio
import json
import time

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
# JSON STORAGE
# =======================

DATA_FILE = "cards.json"

def load_data():
    if not os.path.exists(DATA_FILE):
        return {"cards": {}, "players": {}, "drop_channels": {}}
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

data = load_data()

# Cooldowns
work_cooldown = {}
daily_cooldown = {}

# =======================
# EVENTS
# =======================

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    # start the random drop loop inside on_ready
    bot.loop.create_task(random_drop_loop())

# =======================
# HELP
# =======================

@bot.command()
async def help(ctx):
    embed = discord.Embed(
        title="📜 Commands",
        color=discord.Color.purple()
    )
    embed.add_field(name="!start", value="Start your card journey", inline=False)
    embed.add_field(name="!balance", value="Check your coins", inline=False)
    embed.add_field(name="!work", value="Earn coins + card (30s cooldown)", inline=False)
    embed.add_field(name="!daily", value="Daily reward + card (24h)", inline=False)
    embed.add_field(name="!mycards", value="View your cards", inline=False)
    embed.add_field(name="!setdrop #channel", value="Set the random drop channel (admin only)", inline=False)
    await ctx.send(embed=embed)

# =======================
# START
# =======================

@bot.command()
async def start(ctx):
    user_id = str(ctx.author.id)
    if user_id in data["players"]:
        await ctx.send("You already started 💜")
        return

    if not data["cards"]:
        await ctx.send("⚠ No cards found in cards.json!")
        return

    # pick a random member and rarity 1 for starter
    members = list(data["cards"].keys())
    while True:
        member = random.choice(members)
        if "1" in data["cards"][member]:
            rarity = "1"
            break
    card_info = data["cards"][member][rarity]

    data["players"][user_id] = {
        "coins": 500,
        "cards": [f"{card_info['name']} ({rarity}★)"]
    }

    save_data(data)

    embed = discord.Embed(
        title="🎉 Welcome!",
        description=f"💰 500 coins\n🃏 Starter: {card_info['name']} ({rarity}★)",
        color=discord.Color.purple()
    )
    embed.set_image(url=card_info["image"])
    await ctx.send(embed=embed)

# =======================
# BALANCE
# =======================

@bot.command()
async def balance(ctx):
    user_id = str(ctx.author.id)
    if user_id not in data["players"]:
        await ctx.send("Use `!start` first 💜")
        return
    coins = data["players"][user_id]["coins"]
    await ctx.send(f"💰 You have {coins} coins.")

# =======================
# WORK
# =======================

@bot.command()
async def work(ctx):
    user_id = str(ctx.author.id)
    if user_id not in data["players"]:
        await ctx.send("Use `!start` first 💜")
        return

    now = asyncio.get_event_loop().time()
    if user_id in work_cooldown and work_cooldown[user_id] > now:
        remaining = int(work_cooldown[user_id] - now)
        await ctx.send(f"⏳ Wait {remaining}s before working again.")
        return

    earned = random.randint(50, 150)
    data["players"][user_id]["coins"] += earned

    member = random.choice(list(data["cards"].keys()))
    rarity = random.choice(list(data["cards"][member].keys()))
    card_info = data["cards"][member][rarity]

    card_name = f"{card_info['name']} ({rarity}★)"
    data["players"][user_id]["cards"].append(card_name)
    save_data(data)

    work_cooldown[user_id] = now + 30

    embed = discord.Embed(
        title="💼 You worked!",
        description=f"💰 +{earned} coins\n🃏 {card_name}",
        color=discord.Color.purple()
    )
    embed.set_image(url=card_info["image"])
    await ctx.send(embed=embed)

# =======================
# DAILY
# =======================

@bot.command()
async def daily(ctx):
    user_id = str(ctx.author.id)
    if user_id not in data["players"]:
        await ctx.send("Use `!start` first 💜")
        return

    now = asyncio.get_event_loop().time()
    if user_id in daily_cooldown and daily_cooldown[user_id] > now:
        remaining = int(daily_cooldown[user_id] - now)
        hours = remaining // 3600
        minutes = (remaining % 3600) // 60
        await ctx.send(f"⏳ Come back in {hours}h {minutes}m.")
        return

    reward = 500
    data["players"][user_id]["coins"] += reward

    member = random.choice(list(data["cards"].keys()))
    rarity = random.choice(list(data["cards"][member].keys()))
    card_info = data["cards"][member][rarity]

    card_name = f"{card_info['name']} ({rarity}★)"
    data["players"][user_id]["cards"].append(card_name)
    save_data(data)

    daily_cooldown[user_id] = now + 86400

    embed = discord.Embed(
        title="🎁 Daily Reward!",
        description=f"💰 +{reward} coins\n🃏 {card_name}",
        color=discord.Color.purple()
    )
    embed.set_image(url=card_info["image"])
    await ctx.send(embed=embed)

# =======================
# MY CARDS
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

    index = 0

    def create_embed(i):
        card_string = cards[i]
        member = card_string.split(" ")[0]
        rarity = card_string.split("(")[1].split("★")[0]
        card_data = data["cards"].get(member, {}).get(rarity)

        embed = discord.Embed(
            title=f"🃏 {card_string}",
            color=discord.Color.purple()
        )
        if card_data:
            embed.set_image(url=card_data["image"])
        embed.set_footer(text=f"{i+1}/{len(cards)}")
        return embed

    message = await ctx.send(embed=create_embed(index))
    if len(cards) == 1:
        return

    await message.add_reaction("⬅️")
    await message.add_reaction("➡️")

    def check(reaction, user):
        return user == ctx.author and str(reaction.emoji) in ["⬅️", "➡️"] and reaction.message.id == message.id

    while True:
        try:
            reaction, user = await bot.wait_for("reaction_add", timeout=120, check=check)
            if str(reaction.emoji) == "➡️":
                index = (index + 1) % len(cards)
            else:
                index = (index - 1) % len(cards)
            await message.edit(embed=create_embed(index))
            await message.remove_reaction(reaction, user)
        except asyncio.TimeoutError:
            break

# =======================
# SET DROP CHANNEL
# =======================

@bot.command()
@commands.has_permissions(administrator=True)
async def setdrop(ctx, channel: discord.TextChannel):
    data["drop_channels"][str(ctx.guild.id)] = channel.id
    save_data(data)
    await ctx.send(f"✅ Drops will now appear in {channel.mention}")

# =======================
# RANDOM DROP LOOP
# =======================

async def random_drop_loop():
    await bot.wait_until_ready()
    while not bot.is_closed():
        for guild in bot.guilds:
            channel_id = data["drop_channels"].get(str(guild.id))
            if not channel_id:
                continue
            channel = bot.get_channel(channel_id)
            if not channel:
                continue

            players_in_guild = [
                user_id for user_id in data["players"]
                if guild.get_member(int(user_id))
            ]
            if not players_in_guild:
                continue

            user_id = random.choice(players_in_guild)
            member = guild.get_member(int(user_id))

            card_member = random.choice(list(data["cards"].keys()))
            rarity = random.choice(list(data["cards"][card_member].keys()))
            card_info = data["cards"][card_member][rarity]
            card_name = f"{card_info['name']} ({rarity}★)"

            data["players"][user_id]["cards"].append(card_name)
            save_data(data)

            embed = discord.Embed(
                title="🎴 Random Drop!",
                description=f"{member.mention} received: **{card_name}**",
                color=discord.Color.purple()
            )
            embed.set_image(url=card_info["image"])
            await channel.send(embed=embed)

        await asyncio.sleep(600)  # 10 minutes

# =======================
# AUTO-RECONNECT RUN
# =======================

def start_bot():
    TOKEN = os.environ.get("DISCORD_TOKEN")
    while True:
        try:
            bot.run(TOKEN)
        except Exception as e:
            print("Bot crashed:", e)
            print("Restarting in 5 seconds...")
            time.sleep(5)

# =======================
# MAIN
# =======================

if __name__ == "__main__":
    keep_alive()
    start_bot()
