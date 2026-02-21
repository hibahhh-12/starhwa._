# ================= IMPORTS =================
import os
import json
import random
import datetime
import asyncio

import discord
from discord.ext import commands

from flask import Flask
from threading import Thread


# ================= CONSTANTS =================
EMBED_COLOR = discord.Color.from_rgb(147, 112, 219)
DATA_FILE = "cards.json"
WORK_COOLDOWN = 1800     # 30 min
DAILY_COOLDOWN = 86400   # 24 hours

# ================= FLASK KEEPALIVE =================
import os
from flask import Flask
from threading import Thread

app = Flask('')

@app.route('/')
def home():
    return "Seonghwa Bot is alive 💜"

def run():
    # Use Render's PORT environment variable
    port = int(os.environ.get("PORT", 8080))  # fallback to 8080 if PORT not set
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.start()

# ================= BOT SETUP =================
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

keep_alive()  # start the Flask server for UptimeRobot
import os

TOKEN = os.environ.get("DISCORD_TOKEN")  # pull it safely from Render's env variables
if not TOKEN:
    print("ERROR: DISCORD_TOKEN not found!")
else:
    bot.run(TOKEN)

# ================= DATA LOAD/ SAVE =================
def load_data():
    if not os.path.exists(DATA_FILE):
        return {"cards": {}, "players": {}}
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

data = load_data()

# ================= HELP =================
@bot.command()
async def help(ctx):
    embed = discord.Embed(
        title="💜 K-POP and T-POP Card Bot !",
        description="Collect cards, earn coins, and flex your collection ✨",
        color=EMBED_COLOR
    )
    embed.add_field(
        name="🎮 Getting Started",
        value="`!start` → Get starter coins + first card\n"
              "`!coins` → Check balance",
        inline=False
    )
    embed.add_field(
        name="💼 Rewards",
        value="`!work` → Coins + random card (30 min cooldown)\n"
              "`!daily` → Big reward + card (24h cooldown)",
        inline=False
    )
    embed.add_field(
        name="📚 Collection",
        value="`!mycards` → View all your cards (paged)",
        inline=False
    )
    embed.set_footer(text=f"Requested by {ctx.author.display_name} 💜")
    await ctx.send(embed=embed)

# ================= START =================
@bot.command()
async def start(ctx):
    user_id = str(ctx.author.id)
    if user_id in data["players"]:
        await ctx.send("You already started 💜")
        return
    if not data["cards"]:
        await ctx.send("⚠ No cards loaded in cards.json!")
        return

    # Pick starter card
    member = random.choice(list(data["cards"].keys()))
    rarity = random.choice(list(data["cards"][member].keys()))
    card_name = data["cards"][member][rarity]["name"]

    data["players"][user_id] = {
        "coins": 1000,
        "cards": [f"{card_name} ({rarity}★)"],
        "last_work": None,
        "last_daily": None,
        "started": True
    }
    save_data(data)

    embed = discord.Embed(
        title="🎉 Welcome!",
        description=f"You received:\n💰 1000 coins\n🃏 {card_name}",
        color=EMBED_COLOR
    )
    embed.set_image(url=data["cards"][member][rarity]["image"])
    await ctx.send(embed=embed)

# ================= COINS =================
@bot.command()
async def coins(ctx):
    user_id = str(ctx.author.id)
    if user_id not in data["players"]:
        await ctx.send("Use `!start` first 💜")
        return
    coins_amount = data["players"][user_id]["coins"]
    embed = discord.Embed(
        title="💰 Your Coins",
        description=f"You have **{coins_amount} coins**",
        color=EMBED_COLOR
    )
    await ctx.send(embed=embed)

# ================= WORK (30 MIN COOLDOWN) =================
@bot.command()
async def work(ctx):
    user_id = str(ctx.author.id)

    if user_id not in data["players"]:
        await ctx.send("Use `!start` first 💜")
        return

    player = data["players"][user_id]

    # safety check for old users
    if "last_work" not in player:
        player["last_work"] = None

    now = datetime.datetime.now(datetime.timezone.utc)  # aware UTC datetime

    if player["last_work"]:
        last_work = datetime.datetime.fromisoformat(player["last_work"])
        # convert to aware if stored datetime is naive
        if last_work.tzinfo is None:
            last_work = last_work.replace(tzinfo=datetime.timezone.utc)

        diff = now - last_work
        if diff.total_seconds() < 1800:
            remaining = 1800 - diff.total_seconds()
            minutes = int(remaining // 60)
            seconds = int(remaining % 60)
            await ctx.send(f"⏳ You already worked! Try again in {minutes}m {seconds}s.")
            return

    # reward
    coins_earned = random.randint(100, 300)
    player["coins"] += coins_earned

    # random card
    member = random.choice(list(data["cards"].keys()))
    rarity = random.choice(list(data["cards"][member].keys()))
    card_name = f"{data['cards'][member][rarity]['name']} ({rarity}★)"
    player["cards"].append(card_name)

    player["last_work"] = now.isoformat()  # store aware datetime
    save_data(data)

    embed = discord.Embed(
        title="💼 You Worked!",
        description=f"You earned **{coins_earned} coins**\nAnd got 🃏 {card_name}",
        color=EMBED_COLOR
    )
    embed.set_image(url=data["cards"][member][rarity]["image"])
    await ctx.send(embed=embed)


# ================= DAILY (24H COOLDOWN) =================
@bot.command()
async def daily(ctx):
    user_id = str(ctx.author.id)

    if user_id not in data["players"]:
        await ctx.send("Use `!start` first 💜")
        return

    player = data["players"][user_id]

    # safety check for old users
    if "last_daily" not in player:
        player["last_daily"] = None

    now = datetime.datetime.now(datetime.timezone.utc)  # aware UTC datetime

    if player["last_daily"]:
        last_daily = datetime.datetime.fromisoformat(player["last_daily"])
        # convert to aware if stored datetime is naive
        if last_daily.tzinfo is None:
            last_daily = last_daily.replace(tzinfo=datetime.timezone.utc)

        diff = now - last_daily
        if diff.total_seconds() < 86400:
            remaining = 86400 - diff.total_seconds()
            hours = int(remaining // 3600)
            minutes = int((remaining % 3600) // 60)
            await ctx.send(f"⏳ You already claimed daily! Try again in {hours}h {minutes}m.")
            return

    # reward
    coins_earned = 500
    player["coins"] += coins_earned

    member = random.choice(list(data["cards"].keys()))
    rarity = random.choice(list(data["cards"][member].keys()))
    card_name = f"{data['cards'][member][rarity]['name']} ({rarity}★)"
    player["cards"].append(card_name)

    player["last_daily"] = now.isoformat()  # store aware datetime
    save_data(data)

    embed = discord.Embed(
        title="🌟 Daily Reward!",
        description=f"You received **{coins_earned} coins** + a random card!",
        color=EMBED_COLOR
    )
    embed.add_field(name="New Card", value=card_name)
    embed.set_image(url=data["cards"][member][rarity]["image"])
    await ctx.send(embed=embed)
# ================= MYCARDS PAGINATED =================
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

    page = 0
    max_pages = len(cards)

    def get_embed(page_index):
        card_name = cards[page_index]
        image_url = None
        for member in data["cards"]:
            for rarity in data["cards"][member]:
                if data["cards"][member][rarity]["name"] in card_name:
                    image_url = data["cards"][member][rarity]["image"]
        embed = discord.Embed(
            title=f"🃏 {card_name} ({page_index + 1}/{max_pages})",
            color=EMBED_COLOR
        )
        if image_url:
            embed.set_image(url=image_url)
        return embed

    msg = await ctx.send(embed=get_embed(page))
    if max_pages == 1:
        return

    await msg.add_reaction("◀️")
    await msg.add_reaction("▶️")

    def check(reaction, user):
        return user == ctx.author and str(reaction.emoji) in ["◀️", "▶️"] and reaction.message.id == msg.id

    while True:
        try:
            reaction, user = await bot.wait_for("reaction_add", timeout=120.0, check=check)
            if str(reaction.emoji) == "▶️":
                page = (page + 1) % max_pages
            elif str(reaction.emoji) == "◀️":
                page = (page - 1) % max_pages
            await msg.edit(embed=get_embed(page))
            await msg.remove_reaction(reaction, user)
        except asyncio.TimeoutError:
            break














