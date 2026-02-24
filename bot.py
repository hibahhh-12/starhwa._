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

DATA_FILE = "starhwa_data.json"
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
        # Fallback if file is empty
        return {"cards": {}, "players": {}, "guilds": {}, "market": []}

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
        
        # Wishlist Check
        for wish_uid, u_info in data["players"].items():
            if any(w.lower() in card['name'].lower() for w in u_info.get("wishlist", [])):
                if wish_uid != uid: await interaction.channel.send(f"🔔 <@{wish_uid}>, your wish **{card['name']}** dropped!")

        await interaction.response.send_message(f"✨ **{interaction.user.name}** caught **{card['name']}**!")

    @discord.ui.button(label="1", style=discord.ButtonStyle.secondary)
    async def b1(self, i, b): await self.claim(i, 0)
    @discord.ui.button(label="2", style=discord.ButtonStyle.secondary)
    async def b2(self, i, b): await self.claim(i, 1)
    @discord.ui.button(label="3", style=discord.ButtonStyle.secondary)
    async def b3(self, i, b): await self.claim(i, 2)

class TradeView(discord.ui.View):
    def __init__(self, s, r, s_c, r_c):
        super().__init__(timeout=180)
        self.s, self.r, self.s_c, self.r_c = s, r, s_c, r_c
        self.s_ok, self.r_ok = False, False

    @discord.ui.button(label="Confirm Trade", style=discord.ButtonStyle.green)
    async def ok(self, i, b):
        if i.user.id == self.s.id: self.s_ok = True
        elif i.user.id == self.r.id: self.r_ok = True
        else: return await i.response.send_message("Not your trade!", ephemeral=True)
        
        if self.s_ok and self.r_ok:
            data["players"][str(self.s.id)]["cards"].remove(self.s_c)
            data["players"][str(self.r.id)]["cards"].remove(self.r_c)
            data["players"][str(self.s.id)]["cards"].append(self.r_c)
            data["players"][str(self.r.id)]["cards"].append(self.s_c)
            save_data(data)
            await i.message.edit(content="✅ Trade Complete!", view=None)
        await i.response.send_message("Confirmed!", ephemeral=True)

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
    await interaction.response.send_message("✨ Welcome to **Starhwa**. Inspired by Seonghwa, you can now collect ATEEZ!")

@bot.tree.command(name="drop", description="Spawn 3 random ATEEZ idols")
async def drop(interaction: discord.Interaction):
    gid = str(interaction.guild.id)
    chan_id = data["guilds"].get(gid, {}).get("drop_channel")
    if chan_id and interaction.channel_id != chan_id:
        return await interaction.response.send_message(f"❌ Please use the drop channel: <#{chan_id}>", ephemeral=True)

    dropped_cards = []
    embed = discord.Embed(title="🌌 Starhwa Cosmic Drop", description="Claim your favorite ATEEZ member!", color=0x2b2d31)
    
    # Selection logic using YOUR JSON structure
    for i in range(3):
        member_name = random.choice(list(data["cards"].keys()))
        rarity_level = random.choice(list(data["cards"][member_name].keys()))
        card_data = data["cards"][member_name][rarity_level]
        
        # Save necessary info for claiming
        card_obj = {
            "name": card_data["name"],
            "member": member_name,
            "rarity": rarity_level,
            "image": card_data["image"]
        }
        dropped_cards.append(card_obj)
        embed.add_field(name=f"Slot {i+1}", value=f"**{card_data['name']}**\n{rarity_level}★", inline=True)
    
    embed.set_image(url=dropped_cards[0]["image"])
    await interaction.response.send_message(embed=embed, view=DropView(dropped_cards))

@bot.tree.command(name="inventory", description="View your card binder")
async def inventory(interaction: discord.Interaction, idol: str = None):
    uid = str(interaction.user.id)
    if uid not in data["players"]: return await interaction.response.send_message("Run `/start`!")
    
    cards = data["players"][uid]["cards"]
    if idol:
        cards = [c for c in cards if idol.lower() in c['member'].lower() or idol.lower() in c['name'].lower()]
    
    inv_text = "\n".join([f"• **{c['name']}** ({c['rarity']}★)" for c in cards[:15]])
    embed = discord.Embed(title=f"🎴 {interaction.user.name}'s Binder", description=inv_text or "No cards found.", color=0x9b59b6)
    embed.set_footer(text=f"Total: {len(cards)} cards")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="view", description="View a card in high definition")
async def view(interaction: discord.Interaction, card_name: str):
    uid = str(interaction.user.id)
    card = next((c for c in data["players"][uid]["cards"] if card_name.lower() in c['name'].lower()), None)
    if not card: return await interaction.response.send_message("Card not found in your inventory!", ephemeral=True)
    
    embed = discord.Embed(title=card['name'], color=0xf1c40f)
    embed.set_image(url=card['image'])
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="work", description="Play RPS for Beads")
async def work(interaction: discord.Interaction):
    uid = str(interaction.user.id)
    now = time.time()
    if now - data["players"][uid].get("work", 0) < 1800:
        return await interaction.response.send_message("⏳ Seonghwa says rest! 30m cooldown.", ephemeral=True)

    await interaction.response.send_message("✊ **Rock, Paper, or Scissors?**")
    def check(m): return m.author == interaction.user and m.content.lower() in ["rock", "paper", "scissors"]
    try:
        msg = await bot.wait_for("message", timeout=20, check=check)
        bot_choice = random.choice(["rock", "paper", "scissors"])
        user_choice = msg.content.lower()
        
        if user_choice == bot_choice: res, beads = "🤝 Tie!", 150
        elif (user_choice=="rock" and bot_choice=="scissors") or (user_choice=="paper" and bot_choice=="rock") or (user_choice=="scissors" and bot_choice=="paper"):
            res, beads = "🏆 Win!", 400
        else: res, beads = "💀 Lose!", 50

        data["players"][uid]["beads"] += beads
        data["players"][uid]["work"] = now
        save_data(data)
        await interaction.followup.send(f"**{res}** Bot chose {bot_choice}. Earned 💰 {beads} Beads!")
    except asyncio.TimeoutError: await interaction.followup.send("⏰ Too slow!")

@bot.tree.command(name="setchannel", description="Admin: Set drop channel")
@app_commands.checks.has_permissions(manage_channels=True)
async def setchannel(interaction: discord.Interaction, channel: discord.TextChannel):
    gid = str(interaction.guild.id)
    if gid not in data["guilds"]: data["guilds"][gid] = {}
    data["guilds"][gid]["drop_channel"] = channel.id
    save_data(data)
    await interaction.response.send_message(f"✅ Drops set to {channel.mention}!")

@bot.tree.command(name="profile", description="Check your stats")
async def profile(interaction: discord.Interaction, user: discord.Member = None):
    user = user or interaction.user
    p = data["players"].get(str(user.id))
    if not p: return await interaction.response.send_message("User not registered!")
    embed = discord.Embed(title=f"👤 {user.name}'s Profile", color=0x3498db)
    embed.add_field(name="💰 Beads", value=p["beads"])
    embed.add_field(name="🎴 Cards", value=len(p["cards"]))
    embed.set_thumbnail(url=user.avatar.url if user.avatar else None)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="leaderboard", description="Rich list")
async def leaderboard(interaction: discord.Interaction):
    top = sorted(data["players"].items(), key=lambda x: x[1].get("beads", 0), reverse=True)[:10]
    lb = "\n".join([f"**#{i+1}** <@{k}> — 💰 {v['beads']}" for i, (k,v) in enumerate(top)])
    await interaction.response.send_message(embed=discord.Embed(title="🏆 Global Leaderboard", description=lb or "No users yet!"))

# =======================
# 🚀 RUN STARHWA
# =======================
if __name__ == "__main__":
    keep_alive()
    bot.run(os.environ.get("DISCORD_TOKEN"))
