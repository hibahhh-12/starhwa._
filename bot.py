import discord
from discord.ext import commands
from flask import Flask
import threading
import os
import random
import asyncio
import json
import time
from github import Github

# =======================
# KEEP ALIVE (Flask)
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

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

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

# =======================
# GITHUB SYNC
# =======================
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
GITHUB_REPO = os.environ.get("GITHUB_REPO")  # format: username/repo

g = Github(GITHUB_TOKEN) if GITHUB_TOKEN else None
repo = g.get_repo(GITHUB_REPO) if g else None

def push_json_to_github():
    if not repo:
        return
    try:
        with open(DATA_FILE, "r") as f:
            content = f.read()
        file = repo.get_contents(DATA_FILE)
        repo.update_file(path=DATA_FILE, message=f"Update by bot", content=content, sha=file.sha)
        print("cards.json pushed to GitHub ✅")
    except Exception as e:
        print("Failed to push to GitHub:", e)

def load_data_from_github():
    if not repo:
        return load_data()
    try:
        file = repo.get_contents(DATA_FILE)
        content = file.decoded_content.decode()
        with open(DATA_FILE, "w") as f:
            f.write(content)
        print("Loaded cards.json from GitHub ✅")
        return json.loads(content)
    except Exception as e:
        print("Failed to load from GitHub, loading local file instead:", e)
        return load_data()

data = load_data_from_github()

# =======================
# COOLDOWNS
# =======================
work_cooldown = {}
daily_cooldown = {}

# =======================
# BOT EVENTS
# =======================
@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user} ✅")
    bot.loop.create_task(random_drop_loop())

# =======================
# HELPER FUNCTIONS
# =======================
def check_work_cooldown(user_id):
    now = time.time()
    return now - work_cooldown.get(user_id, 0) < 30  # 30s cooldown

def check_daily_cooldown(user_id):
    now = time.time()
    return now - daily_cooldown.get(user_id, 0) < 86400  # 24h cooldown

# =======================
# COMMANDS
# =======================
@bot.command()
async def help(ctx):
    embed = discord.Embed(title="📜 Commands", color=discord.Color.purple())
    embed.add_field(name="!start", value="Start your card journey", inline=False)
    embed.add_field(name="!balance", value="Check your coins", inline=False)
    embed.add_field(name="!work", value="Play mini-games to earn coins & cards (30s cooldown)", inline=False)
    embed.add_field(name="!daily", value="Daily reward + card (24h)", inline=False)
    embed.add_field(name="!mycards", value="View your cards", inline=False)
    embed.add_field(name="!setchannel #channel", value="Set the drop channel for random card drops", inline=False)
    await ctx.send(embed=embed)

@bot.command()
async def start(ctx):
    user_id = str(ctx.author.id)
    if user_id in data["players"]:
        await ctx.send("You already started 💜")
        return
    if not data["cards"]:
        await ctx.send("⚠ No cards found in cards.json!")
        return

    member = random.choice(list(data["cards"].keys()))
    rarity = random.choice(list(data["cards"][member].keys()))
    card_info = data["cards"][member][rarity]

    data["players"][user_id] = {"coins": 500, "cards": [f"{card_info['name']} ({rarity}★)"]}
    save_data(data)
    push_json_to_github()

    embed = discord.Embed(
        title="🎉 Welcome!",
        description=f"💰 500 coins\n🃏 Starter: {card_info['name']} ({rarity}★)",
        color=discord.Color.purple()
    )
    embed.set_image(url=card_info["image"])
    await ctx.send(embed=embed)

@bot.command()
async def balance(ctx):
    user_id = str(ctx.author.id)
    if user_id not in data["players"]:
        await ctx.send("You need to start first with !start")
        return
    coins = data["players"][user_id]["coins"]
    await ctx.send(f"💰 You have {coins} coins!")

@bot.command()
async def mycards(ctx):
    user_id = str(ctx.author.id)
    if user_id not in data["players"]:
        await ctx.send("You need to start first with !start")
        return
    cards = data["players"][user_id]["cards"]
    if not cards:
        await ctx.send("You have no cards yet.")
        return
    embed = discord.Embed(title=f"{ctx.author.name}'s Cards", color=discord.Color.purple())
    embed.description = "\n".join(cards)
    await ctx.send(embed=embed)

@bot.command()
async def work(ctx):
    user_id = str(ctx.author.id)
    if user_id not in data["players"]:
        await ctx.send("You need to start first with !start")
        return
    if check_work_cooldown(user_id):
        await ctx.send("⏱ Wait 30s between works!")
        return

    coins_earned = random.randint(50, 200)
    data["players"][user_id]["coins"] += coins_earned

    # 50% chance to get a random card
    if random.random() < 0.5 and data["cards"]:
        card_member = random.choice(list(data["cards"].keys()))
        rarity = random.choice(list(data["cards"][card_member].keys()))
        card_info = data["cards"][card_member][rarity]
        card_name = f"{card_info['name']} ({rarity}★)"
        data["players"][user_id]["cards"].append(card_name)
        await ctx.send(f"💰 You earned {coins_earned} coins and got a card: {card_name}")
    else:
        await ctx.send(f"💰 You earned {coins_earned} coins!")

    work_cooldown[user_id] = time.time()
    save_data(data)
    push_json_to_github()

@bot.command()
async def daily(ctx):
    user_id = str(ctx.author.id)
    if user_id not in data["players"]:
        await ctx.send("You need to start first with !start")
        return
    if check_daily_cooldown(user_id):
        await ctx.send("⏱ Daily already claimed! Wait 24h.")
        return

    coins_earned = random.randint(300, 700)
    data["players"][user_id]["coins"] += coins_earned

    card_member = random.choice(list(data["cards"].keys()))
    rarity = random.choice(list(data["cards"][card_member].keys()))
    card_info = data["cards"][card_member][rarity]
    card_name = f"{card_info['name']} ({rarity}★)"
    data["players"][user_id]["cards"].append(card_name)

    daily_cooldown[user_id] = time.time()
    save_data(data)
    push_json_to_github()

    await ctx.send(f"🌞 Daily reward: {coins_earned} coins + card: {card_name}")

@bot.command()
async def setchannel(ctx, channel: discord.TextChannel):
    guild_id = str(ctx.guild.id)
    data["drop_channels"][guild_id] = channel.id
    save_data(data)
    await ctx.send(f"✅ Random drops will now appear in {channel.mention}")

# =======================
# RANDOM DROP LOOP
# =======================
async def random_drop_loop():
    await bot.wait_until_ready()
    while not bot.is_closed():
        for guild in bot.guilds:
            guild_id = str(guild.id)
            channel_id = data["drop_channels"].get(guild_id)
            if not channel_id:
                continue
            channel = bot.get_channel(channel_id)
            if not channel:
                continue
            players_in_guild = [
                uid for uid in data["players"].keys() if int(uid) in [m.id for m in guild.members]
            ]
            if not players_in_guild:
                continue
            user_id = random.choice(players_in_guild)
            member = guild.get_member(int(user_id))
            if not member:
                continue
            card_member = random.choice(list(data["cards"].keys()))
            rarity = random.choice(list(data["cards"][card_member].keys()))
            card_info = data["cards"][card_member][rarity]
            card_name = f"{card_info['name']} ({rarity}★)"
            data["players"][user_id]["cards"].append(card_name)
            save_data(data)
            push_json_to_github()
            embed = discord.Embed(
                title="🎴 Random Drop!",
                description=f"{member.mention} received: **{card_name}**",
                color=discord.Color.purple()
            )
            embed.set_image(url=card_info["image"])
            await channel.send(embed=embed)
        await asyncio.sleep(600)  # every 10 mins

# =======================
# RUN BOT
# =======================
def start_bot():
    TOKEN = os.environ.get("DISCORD_TOKEN")
    bot.run(TOKEN)

# =======================
# MAIN
# =======================
if __name__ == "__main__":
    keep_alive()
    start_bot()
