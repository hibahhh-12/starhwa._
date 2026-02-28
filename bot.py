import discord
from discord.ext import commands
from flask import Flask
import threading
import os
import asyncio
import time

# =======================
# FLASK KEEP-ALIVE
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
# DISCORD TOKEN + CLEANUP
# =======================
TOKEN = os.environ.get("DISCORD_TOKEN", "").replace("\u00A0","").strip()

if not TOKEN:
    print("❌ ERROR: DISCORD_TOKEN not found or empty!")
    exit()

print(f"🔑 Token length after cleanup: {len(TOKEN)}")

# =======================
# BOT SETUP
# =======================
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.reactions = True

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

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
# AUTO-RESTART
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
