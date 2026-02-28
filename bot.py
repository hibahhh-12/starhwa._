import discord
from discord.ext import commands
from flask import Flask
import threading
import os
import asyncio
import time

# =======================
# KEEP ALIVE (Render)
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
# BOT SETUP
# =======================
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.reactions = True

bot = commands.Bot(
    command_prefix="!",
    intents=intents,
    help_command=None
)

# =======================
# EVENTS
# =======================
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

# =======================
# TEST COMMAND
# =======================
@bot.command()
async def ping(ctx):
    await ctx.send("Pong!")

# =======================
# AUTO-RECONNECT
# =======================
def start_bot():
    TOKEN = os.environ.get("DISCORD_TOKEN")

    if not TOKEN:
        print("ERROR: DISCORD_TOKEN not found in environment variables.")
        return

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
