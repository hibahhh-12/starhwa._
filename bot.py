import discord
from discord.ext import commands
from discord import app_commands
from flask import Flask
import threading, os, random, asyncio, json, time, datetime
from github import Github

# =======================
# 🌐 KEEP ALIVE & SYNC
# =======================
app = Flask('')
@app.route('/')
def home(): return "Starhwa is Online! ✨"
def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive():
    t = threading.Thread(target=run)
    t.daemon = True
    t.start()

DATA_FILE = "cards.json"
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
GITHUB_REPO = os.environ.get("GITHUB_REPO")
g = Github(GITHUB_TOKEN)
repo = g.get_repo(GITHUB_REPO)

def save_data(data_obj):
    try:
        content = json.dumps(data_obj, indent=4)
        with open(DATA_FILE, "w") as f: f.write(content)
        file = repo.get_contents(DATA_FILE)
        repo.update_file(path=DATA_FILE, message="Starhwa Update", content=content, sha=file.sha)
    except Exception as e: print(f"Sync Error: {e}")

def load_data():
    try:
        file = repo.get_contents(DATA_FILE)
        return json.loads(file.decoded_content.decode())
    except: 
        return {"cards": {}, "players": {}, "guilds": {}}

data = load_data()

# =======================
# 🤖 BOT SETUP
# =======================
class StarhwaBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=discord.Intents.all())
    async def setup_hook(self):
        await self.tree.sync()
        print(f"Starhwa Slash Commands Synced!")

bot = StarhwaBot()

# =======================
# 🍱 UI COMPONENTS
# =======================
class DropView(discord.ui.View):
    def __init__(self, cards_to_show):
        super().__init__(timeout=60)
        self.cards = cards_to_show
        self.claimed = [False, False, False]

    async def claim(self, interaction, idx):
        uid = str(interaction.user.id)
        if uid not in data["players"]: 
            return await interaction.response.send_message("Use `/start` first!", ephemeral=True)
        if self.claimed[idx]: 
            return await interaction.response.send_message("This star has already been claimed!", ephemeral=True)
        
        card = self.cards[idx]
        data["players"][uid]["cards"].append(card)
        self.claimed[idx] = True
        save_data(data)
        
        await interaction.response.send_message(f"✨ **{interaction.user.name}** caught **{card['name']}**!")

    @discord.ui.button(label="1", style=discord.ButtonStyle.secondary)
    async def b1(self, i, b): await self.claim(i, 0)
    @discord.ui.button(label="2", style=discord.ButtonStyle.secondary)
    async def b2(self, i, b): await self.claim(i, 1)
    @discord.ui.button(label="3", style=discord.ButtonStyle.secondary)
    async def b3(self, i, b): await self.claim(i, 2)

# =======================
# ⚔️ SLASH COMMANDS
# =======================

@bot.tree.command(name="start", description="Begin your Starhwa journey")
async def start(interaction: discord.Interaction):
    uid = str(interaction.user.id)
    if uid in data["players"]: return await interaction.response.send_message("You've already started!")
    data["players"][uid] = {
        "beads": 500, "cards": [], "wishlist": [], "fav": None, 
        "daily": 0, "work": 0, "joined": str(datetime.date.today())
    }
    save_data(data)
    await interaction.response.send_message("✨ Welcome to **Starhwa**. Inspired by Seonghwa!")

@bot.tree.command(name="daily", description="Claim 500 Beads and a random ATEEZ card!")
async def daily(interaction: discord.Interaction):
    uid = str(interaction.user.id)
    if uid not in data["players"]: return await interaction.response.send_message("Run `/start` first!", ephemeral=True)
    
    now = time.time()
    last_daily = data["players"][uid].get("daily", 0)
    if now - last_daily < 86400:
        rem = int(86400 - (now - last_daily))
        return await interaction.response.send_message(f"⏳ Come back in {rem // 3600}h {(rem % 3600) // 60}m.", ephemeral=True)
    
    member_name = random.choice(list(data["cards"].keys()))
    rarity_level = random.choice(list(data["cards"][member_name].keys()))
    card_data = data["cards"][member_name][rarity_level]
    new_card = {"name": card_data["name"], "member": member_name, "rarity": rarity_level, "image": card_data["image"]}

    data["players"][uid]["beads"] += 500
    data["players"][uid]["cards"].append(new_card)
    data["players"][uid]["daily"] = now
    save_data(data)

    embed = discord.Embed(title="🎁 Daily Reward", description="💰 **500 Beads** and a new card!", color=0xffd700)
    embed.add_field(name="Card Found", value=f"✨ **{new_card['name']}**")
    embed.set_image(url=new_card["image"])
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="drop", description="Spawn 3 random ATEEZ idols")
async def drop(interaction: discord.Interaction):
    await interaction.response.defer()
    gid = str(interaction.guild.id)
    chan_id = data["guilds"].get(gid, {}).get("drop_channel")
    if chan_id and interaction.channel_id != chan_id:
        return await interaction.followup.send(f"❌ Use the drop channel: <#{chan_id}>")

    dropped_cards = []
    embed = discord.Embed(title="🌌 Starhwa Cosmic Drop", color=0x2b2d31)
    for i in range(3):
        member_name = random.choice(list(data["cards"].keys()))
        rarity_level = random.choice(list(data["cards"][member_name].keys()))
        card_data = data["cards"][member_name][rarity_level]
        dropped_cards.append({"name": card_data["name"], "member": member_name, "rarity": rarity_level, "image": card_data["image"]})
        embed.add_field(name=f"Slot {i+1}", value=f"**{card_data['name']}**", inline=True)
    
    embed.set_image(url=dropped_cards[0]["image"])
    await interaction.followup.send(embed=embed, view=DropView(dropped_cards))

@bot.tree.command(name="burn", description="Exchange a card for 300 Beads")
async def burn(interaction: discord.Interaction, card_name: str):
    uid = str(interaction.user.id)
    cards = data["players"].get(uid, {}).get("cards", [])
    found = next((c for c in cards if card_name.lower() in c['name'].lower()), None)
    if not found: return await interaction.response.send_message("Card not found!", ephemeral=True)

    cards.remove(found)
    data["players"][uid]["beads"] += 300
    save_data(data)
    await interaction.response.send_message(f"🔥 Burned **{found['name']}** for 💰 300 Beads.")

@bot.tree.command(name="inventory", description="View your binder")
async def inventory(interaction: discord.Interaction):
    uid = str(interaction.user.id)
    cards = data["players"].get(uid, {}).get("cards", [])
    inv_text = "\n".join([f"• {c['name']}" for c in cards[:15]])
    await interaction.response.send_message(embed=discord.Embed(title="🎴 Your Binder", description=inv_text or "Empty."))

@bot.tree.command(name="setchannel", description="Admin: Set drop channel")
@app_commands.checks.has_permissions(manage_channels=True)
async def setchannel(interaction: discord.Interaction, channel: discord.TextChannel):
    await interaction.response.defer()
    gid = str(interaction.guild.id)
    if gid not in data["guilds"]: data["guilds"][gid] = {}
    data["guilds"][gid]["drop_channel"] = channel.id
    save_data(data)
    await interaction.followup.send(f"✅ Drops set to {channel.mention}!")

@bot.tree.command(name="work", description="Play RPS for Beads")
async def work(interaction: discord.Interaction):
    uid = str(interaction.user.id)
    now = time.time()
    if now - data["players"].get(uid, {}).get("work", 0) < 1800:
        return await interaction.response.send_message("⏳ 30m cooldown.", ephemeral=True)

    await interaction.response.send_message("✊ **Rock, Paper, or Scissors?**")
    def check(m): return m.author == interaction.user and m.content.lower() in ["rock", "paper", "scissors"]
    try:
        msg = await bot.wait_for("message", timeout=20, check=check)
        bot_choice = random.choice(["rock", "paper", "scissors"])
        user_choice = msg.content.lower()
        beads = 400 if (user_choice=="rock" and bot_choice=="scissors") or (user_choice=="paper" and bot_choice=="rock") or (user_choice=="scissors" and bot_choice=="paper") else 50
        if user_choice == bot_choice: beads = 150
        data["players"][uid]["beads"] += beads
        data["players"][uid]["work"] = now
        save_data(data)
        await interaction.followup.send(f"Bot chose {bot_choice}. Earned 💰 {beads} Beads!")
    except asyncio.TimeoutError: await interaction.followup.send("⏰ Too slow!")

# =======================
# 🚀 RUN STARHWA
# =======================
if __name__ == "__main__":
    keep_alive()
    bot.run(os.environ.get("DISCORD_TOKEN"))
