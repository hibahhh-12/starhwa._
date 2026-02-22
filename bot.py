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
        title="💜 K-POP and T-POP Card Bot!",
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
        value="`!work` → Coins + random card\n"
              "`!daily` → Big reward + card",
        inline=False
    )
    embed.add_field(
        name="📚 Collection",
        value="`!mycards` → View your cards",
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

    await ctx.send(
        embed=discord.Embed(
            title="💰 Your Coins",
            description=f"You have **{data['players'][user_id]['coins']} coins**",
            color=EMBED_COLOR
        )
    )


# ================= RUN BOT =================
if __name__ == "__main__":
    keep_alive()

    TOKEN = os.environ.get("DISCORD_TOKEN")
    if not TOKEN:
        print("❌ DISCORD_TOKEN not found!")
    else:
        bot.run(TOKEN)
