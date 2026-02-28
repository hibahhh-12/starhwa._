import discord
from discord.ext import commands
from flask import Flask
import threading
import os

# -----------------
# KEEP ALIVE
# -----------------
app = Flask('')

@app.route('/')
def home():
    return "Bot is alive!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = threading.Thread(target=run)
    t.start()

# -----------------
# BOT SETUP
# -----------------
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user} ✅")

# Example command
@bot.command()
async def ping(ctx):
    await ctx.send("Pong!")

# -----------------
# MAIN
# -----------------
if __name__ == "__main__":
    keep_alive()
    TOKEN = os.environ.get("DISCORD_TOKEN")
    bot.run(TOKEN)
