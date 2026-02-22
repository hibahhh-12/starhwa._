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
WORK_COOLDOWN = 1800
DAILY_COOLDOWN = 86400


# ================= FLASK KEEPALIVE =================
app = Flask("")

@app.route("/")
def home():
    return "Seonghwa Bot is alive 💜"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

def keep_alive():
    Thread(target=run_flask).start()


# ================= BOT SETUP =================
intents = discord.Intents.default()
intents.message_content = True
intents.reactions = True

bot = commands.Bot(
    command_prefix="!",
    intents=intents,
    help_command=None
)


# ================= DATA LOAD / SAVE =================
def load_data():
    if not os.path.exists(DATA_FILE):
        return {"cards": {}, "players": {}}
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

data = load_data()


# ================= EVENTS =================
@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")


# ================= HELP =================
@bot.command()
async def help(ctx):
    embed = discord.Embed(
        title="💜 K-POP & T-POP Card Bot",
        description="Collect cards, earn coins, and flex your collection ✨",
        color=EMBED_COLOR
    )
    embed.add_field(
        name="🎮 Getting Started",
        value="`!start` → Starter coins + first card\n"
              "`!coins` → Check balance",
        inline=False
    )
    embed.add_field(
        name="💼 Rewards",
        value="`!work` → Coins + random card (30m cooldown)\n"
              "`!daily` → Big reward + card (24h cooldown)",
        inline=False
    )
    embed.add_field(
        name="📚 Collection",
        value="`!mycards` → View your cards (paged)",
        inline=False
    )
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

    member = random.choice(list(data["cards"].keys()))
    rarity = random.choice(list(data["cards"][member].keys()))
    card_name = data["cards"][member][rarity]["name"]

    data["players"][user_id] = {
        "coins": 1000,
        "cards": [f"{card_name} ({rarity}★)"],
        "last_work": None,
        "last_daily": None
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


# ================= WORK =================
@bot.command()
async def work(ctx):
    user_id = str(ctx.author.id)

    if user_id not in data["players"]:
        await ctx.send("Use `!start` first 💜")
        return

    player = data["players"][user_id]
    now = datetime.datetime.now(datetime.timezone.utc)

    if player["last_work"]:
        last_work = datetime.datetime.fromisoformat(player["last_work"])
        diff = now - last_work
        if diff.total_seconds() < WORK_COOLDOWN:
            remaining = WORK_COOLDOWN - diff.total_seconds()
            minutes = int(remaining // 60)
            seconds = int(remaining % 60)
            await ctx.send(f"⏳ Try again in {minutes}m {seconds}s.")
            return

    coins_earned = random.randint(100, 300)
    player["coins"] += coins_earned

    member = random.choice(list(data["cards"].keys()))
    rarity = random.choice(list(data["cards"][member].keys()))
    card_name = f"{data['cards'][member][rarity]['name']} ({rarity}★)"

    player["cards"].append(card_name)
    player["last_work"] = now.isoformat()

    save_data(data)

    embed = discord.Embed(
        title="💼 You Worked!",
        description=f"💰 +{coins_earned} coins\n🃏 {card_name}",
        color=EMBED_COLOR
    )
    embed.set_image(url=data["cards"][member][rarity]["image"])
    await ctx.send(embed=embed)


# ================= DAILY =================
@bot.command()
async def daily(ctx):
    user_id = str(ctx.author.id)

    if user_id not in data["players"]:
        await ctx.send("Use `!start` first 💜")
        return

    player = data["players"][user_id]
    now = datetime.datetime.now(datetime.timezone.utc)

    if player["last_daily"]:
        last_daily = datetime.datetime.fromisoformat(player["last_daily"])
        diff = now - last_daily
        if diff.total_seconds() < DAILY_COOLDOWN:
            remaining = DAILY_COOLDOWN - diff.total_seconds()
            hours = int(remaining // 3600)
            minutes = int((remaining % 3600) // 60)
            await ctx.send(f"⏳ Try again in {hours}h {minutes}m.")
            return

    coins_earned = 500
    player["coins"] += coins_earned

    member = random.choice(list(data["cards"].keys()))
    rarity = random.choice(list(data["cards"][member].keys()))
    card_name = f"{data['cards'][member][rarity]['name']} ({rarity}★)"

    player["cards"].append(card_name)
    player["last_daily"] = now.isoformat()

    save_data(data)

    embed = discord.Embed(
        title="🌟 Daily Reward!",
        description=f"💰 +{coins_earned} coins\n🃏 {card_name}",
        color=EMBED_COLOR
    )
    embed.set_image(url=data["cards"][member][rarity]["image"])
    await ctx.send(embed=embed)


# ================= MYCARDS =================
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

    def get_embed(index):
        card_name = cards[index]
        image_url = None

        for member in data["cards"]:
            for rarity in data["cards"][member]:
                if data["cards"][member][rarity]["name"] in card_name:
                    image_url = data["cards"][member][rarity]["image"]

        embed = discord.Embed(
            title=f"🃏 {card_name} ({index+1}/{max_pages})",
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
            else:
                page = (page - 1) % max_pages

            await msg.edit(embed=get_embed(page))
            await msg.remove_reaction(reaction, user)

        except asyncio.TimeoutError:
            break


# ================= RUN BOT =================
if __name__ == "__main__":
    keep_alive()

    TOKEN = os.environ.get("DISCORD_TOKEN")
    if not TOKEN:
        print("❌ DISCORD_TOKEN not found!")
    else:
        bot.run(TOKEN)
