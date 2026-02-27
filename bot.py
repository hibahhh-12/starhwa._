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

# =======================
# GITHUB SYNC
# =======================
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
GITHUB_REPO = os.environ.get("GITHUB_REPO")  # e.g., hibahhh-12/starhwa

g = Github(GITHUB_TOKEN)
repo = g.get_repo(GITHUB_REPO)

def push_json_to_github():
    try:
        with open(DATA_FILE, "r") as f:
            content = f.read()
        file = repo.get_contents(DATA_FILE)
        repo.update_file(
            path=DATA_FILE,
            message=f"Update by bot",
            content=content,
            sha=file.sha
        )
        print("cards.json pushed to GitHub ✅")
    except Exception as e:
        print("Failed to push to GitHub:", e)

def load_data_from_github():
    try:
        file = repo.get_contents(DATA_FILE)
        content = file.decoded_content.decode()
        with open(DATA_FILE, "w") as f:
            f.write(content)
        print("Loaded cards.json from GitHub ✅")
        return json.loads(content)
    except Exception as e:
        print("Failed to load from GitHub, loading local file instead:", e)
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, "r") as f:
                return json.load(f)
        return {"cards": {}, "players": {}, "drop_channels": {}}

# Load data
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
    print(f"Logged in as {bot.user}")
    bot.loop.create_task(random_drop_loop())

# =======================
# HELP COMMAND
# =======================
@bot.command()
async def help(ctx):
    embed = discord.Embed(
        title="📜 Commands",
        color=discord.Color.purple()
    )
    embed.add_field(name="!start", value="Start your card journey", inline=False)
    embed.add_field(name="!balance", value="Check your coins", inline=False)
    embed.add_field(name="!work", value="Play mini-games to earn coins & cards (30s cooldown)", inline=False)
    embed.add_field(name="!daily", value="Daily reward + card (24h)", inline=False)
    embed.add_field(name="!mycards", value="View your cards", inline=False)
    embed.add_field(name="!setchannel #channel", value="Set the drop channel for random card drops", inline=False)
    await ctx.send(embed=embed)

# =======================
# START COMMAND
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

    member = random.choice(list(data["cards"].keys()))
    rarity = random.choice(list(data["cards"][member].keys()))
    card_info = data["cards"][member][rarity]

    data["players"][user_id] = {
        "coins": 500,
        "cards": [f"{card_info['name']} ({rarity}★)"]
    }

    save_data(data)
    push_json_to_github()

    embed = discord.Embed(
        title="🎉 Welcome!",
        description=f"💰 500 coins\n🃏 Starter: {card_info['name']} ({rarity}★)",
        color=discord.Color.purple()
    )
    embed.set_image(url=card_info["image"])
    await ctx.send(embed=embed)

# =======================
# BALANCE COMMAND
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
# WORK COMMAND WITH MINI-GAMES
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

    mini_game = random.choice(["dice_roll", "treasure_hunt", "rps", "coin_flip", "lucky_number"])
    coins_earned = 0
    card_earned = None
    description = ""

    if mini_game == "dice_roll":
        roll = random.randint(1, 6)
        coins_earned = roll * 20
        description = f"🎲 You rolled a **{roll}** and earned **{coins_earned} coins**!"
    elif mini_game == "treasure_hunt":
        found = random.choices(["coins", "card"], weights=[70, 30])[0]
        if found == "coins":
            coins_earned = random.randint(50, 200)
            description = f"🗺️ You found a hidden stash with **{coins_earned} coins**!"
        else:
            card_member = random.choice(list(data["cards"].keys()))
            rarity = random.choice(list(data["cards"][card_member].keys()))
            card_info = data["cards"][card_member][rarity]
            card_earned = f"{card_info['name']} ({rarity}★)"
            data["players"][user_id]["cards"].append(card_earned)
            description = f"🗺️ You found a hidden card: **{card_earned}**!"
    elif mini_game == "rps":
        bot_choice = random.choice(["rock", "paper", "scissors"])
        user_choice = random.choice(["rock", "paper", "scissors"])
        coins_earned = random.randint(50, 150)
        description = f"✊ Rock-Paper-Scissors! You chose **{user_choice}**, bot chose **{bot_choice}**.\n"
        if user_choice == bot_choice:
            description += f"🤝 It's a tie! You earned **{coins_earned} coins**."
        elif (user_choice == "rock" and bot_choice == "scissors") or \
             (user_choice == "paper" and bot_choice == "rock") or \
             (user_choice == "scissors" and bot_choice == "paper"):
            coins_earned *= 2
            description += f"🎉 You won! Coins doubled to **{coins_earned} coins**!"
        else:
            coins_earned = coins_earned // 2
            description += f"😢 You lost! Coins halved to **{coins_earned} coins**."
    elif mini_game == "coin_flip":
        result = random.choice(["heads", "tails"])
        guess = random.choice(["heads", "tails"])
        coins_earned = random.randint(50, 150)
        description = f"🪙 Coin flip! You guessed **{guess}**, coin landed on **{result}**.\n"
        if guess == result:
            coins_earned *= 2
            description += f"🎉 Correct! You earned **{coins_earned} coins**!"
        else:
            coins_earned = coins_earned // 2
            description += f"😢 Wrong guess! You earned only **{coins_earned} coins**."
    elif mini_game == "lucky_number":
        number = random.randint(1, 10)
        guess = random.randint(1, 10)
        coins_earned = random.randint(50, 150)
        description = f"🔢 Lucky number! You guessed **{guess}**, lucky number is **{number}**.\n"
        if guess == number:
            coins_earned *= 3
            description += f"🎊 Jackpot! Coins tripled to **{coins_earned} coins**!"
        else:
            description += f"💰 You earned **{coins_earned} coins** anyway."

    data["players"][user_id]["coins"] += coins_earned

    if card_earned is None and random.randint(1,3) == 1:  # 33% chance bonus card
        card_member = random.choice(list(data["cards"].keys()))
        rarity = random.choice(list(data["cards"][card_member].keys()))
        card_info = data["cards"][card_member][rarity]
        card_earned = f"{card_info['name']} ({rarity}★)"
        data["players"][user_id]["cards"].append(card_earned)
        description += f"\n🃏 Bonus card: **{card_earned}**!"

    save_data(data)
    push_json_to_github()
    work_cooldown[user_id] = now + 30

    embed = discord.Embed(
        title="💼 You worked!",
        description=description,
        color=discord.Color.purple()
    )
    if card_earned:
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
    push_json_to_github()

    daily_cooldown[user_id] = now + 86400

    embed = discord.Embed(
        title="🎁 Daily Reward!",
        description=f"💰 +{reward} coins\n🃏 {card_name}",
        color=discord.Color.purple()
    )
    embed.set_image(url=card_info["image"])
    await ctx.send(embed=embed)

# =======================
# MY CARDS COMMAND
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
# SET CHANNEL COMMAND
# =======================
@bot.command()
async def setchannel(ctx, channel: discord.TextChannel):
    guild_id = str(ctx.guild.id)
    data["drop_channels"][guild_id] = channel.id
    save_data(data)
    push_json_to_github()
    await ctx.send(f"✅ Drop channel set to {channel.mention} for this server!")

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
                user_id for user_id in data["players"].keys()
                if int(user_id) in [member.id for member in guild.members]
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

        await asyncio.sleep(600)  # every 10 mins

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

