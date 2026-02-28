import discord
from discord.ext import commands
from flask import Flask
import threading
import os
import asyncio
import json
import time
import random

# =======================
# FLASK KEEP-ALIVE (Render + Uptime Robot)
# =======================
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot is alive!"

def run():
    app.run(host="0.0.0.0", port=8080)

def keep_alive():
    t = threading.Thread(target=run)
    t.start()

# =======================
# DISCORD TOKEN CLEANUP
# =======================
TOKEN = os.environ.get("DISCORD_TOKEN", "").strip()  # removes spaces/newlines
if not TOKEN:
    print("❌ ERROR: DISCORD_TOKEN not found!")
    exit()
print(f"🔑 Token length after strip: {len(TOKEN)}")  # should be ~59–60

# =======================
# BOT SETUP
# =======================
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.reactions = True

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

# =======================
# JSON STORAGE (Safe)
# =======================
DATA_FILE = "cards.json"

def load_data():
    try:
        if not os.path.exists(DATA_FILE):
            return {"cards": {}, "players": {}, "drop_channels": {}}
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    except Exception as e:
        print("❌ Error loading data:", e)
        return {"cards": {}, "players": {}, "drop_channels": {}}

def save_data(data):
    try:
        with open(DATA_FILE, "w") as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        print("❌ Error saving data:", e)

data = load_data()

# =======================
# BOT EVENTS
# =======================
@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user} ✅")

# =======================
# TEST COMMAND
# =======================
@bot.command()
async def ping(ctx):
    await ctx.send("Pong!")

# =======================
# AUTO-RESTART LOOP
# =======================
def start_bot():
    while True:
        try:
            print("⏳ Attempting to start bot...")
            bot.run(TOKEN)
        except Exception as e:
            print("❌ Bot crashed:", e)
            print("⏳ Restarting in 5 seconds...")
            time.sleep(5)

# =======================
# MAIN
# =======================
if __name__ == "__main__":
    print("🚀 Starting Flask keep-alive...")
    keep_alive()
    print("🚀 Starting Discord bot...")
    start_bot()
