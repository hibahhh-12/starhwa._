import discord
from discord.ext import commands
from flask import Flask
import threading
import os
import random
import asyncio

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
# DATA STORAGE
# =======================

coins = {}
work_cooldown = {}
daily_cooldown = {}

# =======================
# EVENTS
# =======================

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

# =======================
# HELP COMMAND
# =======================

@bot.command()
async def help(ctx):
    embed = discord.Embed(
        title="📜 Bot Commands",
        description="Here are the available commands:",
        color=discord.Color.purple()
    )

    embed.add_field(name="💼 !work", value="Earn coins (30s cooldown)", inline=False)
    embed.add_field(name="🎁 !daily", value="Claim daily reward (24h cooldown)", inline=False)
    embed.add_field(name="💰 !balance", value="Check your coins", inline=False)
    embed.add_field(name="🃏 !cards", value="View your cards", inline=False)

    await ctx.send(embed=embed)

# =======================
# BALANCE
# =======================

@bot.command()
async def balance(ctx):
    user = ctx.author.id
    amount = coins.get(user, 0)
    await ctx.send(f"💰 You have {amount} coins.")

# =======================
# WORK COMMAND
# =======================

@bot.command()
async def work(ctx):
    user = ctx.author.id

    if user in work_cooldown:
        if work_cooldown[user] > asyncio.get_event_loop().time():
            remaining = int(work_cooldown[user] - asyncio.get_event_loop().time())
            await ctx.send(f"⏳ Wait {remaining}s before working again.")
            return

    earned = random.randint(50, 150)
    coins[user] = coins.get(user, 0) + earned

    work_cooldown[user] = asyncio.get_event_loop().time() + 30

    await ctx.send(f"💼 You worked and earned {earned} coins!")

# =======================
# DAILY COMMAND
# =======================

@bot.command()
async def daily(ctx):
    user = ctx.author.id

    if user in daily_cooldown:
        if daily_cooldown[user] > asyncio.get_event_loop().time():
            remaining = int(daily_cooldown[user] - asyncio.get_event_loop().time())
            hours = remaining // 3600
            minutes = (remaining % 3600) // 60
            await ctx.send(f"⏳ Come back in {hours}h {minutes}m.")
            return

    reward = 500
    coins[user] = coins.get(user, 0) + reward

    daily_cooldown[user] = asyncio.get_event_loop().time() + 86400

    await ctx.send(f"🎁 You claimed your daily {reward} coins!")

# =======================
# CARD REACTION MENU
# =======================

@bot.command()
async def cards(ctx):
    pages = [
        discord.Embed(title="Page 1", description="Card A\nCard B"),
        discord.Embed(title="Page 2", description="Card C\nCard D"),
        discord.Embed(title="Page 3", description="Card E\nCard F"),
    ]

    current_page = 0
    message = await ctx.send(embed=pages[current_page])

    await message.add_reaction("⬅️")
    await message.add_reaction("➡️")

    def check(reaction, user):
        return user == ctx.author and str(reaction.emoji) in ["⬅️", "➡️"] and reaction.message.id == message.id

    while True:
        try:
            reaction, user = await bot.wait_for("reaction_add", timeout=60, check=check)

            if str(reaction.emoji) == "➡️":
                current_page = (current_page + 1) % len(pages)
            elif str(reaction.emoji) == "⬅️":
                current_page = (current_page - 1) % len(pages)

            await message.edit(embed=pages[current_page])
            await message.remove_reaction(reaction, user)

        except asyncio.TimeoutError:
            break

# =======================
# RUN BOT
# =======================

if __name__ == "__main__":
    keep_alive()
    TOKEN = os.environ.get("DISCORD_TOKEN")
    bot.run(TOKEN)
