import discord
from discord import app_commands
from discord.ext import commands, tasks
import random
import time
import aiosqlite
import aiohttp
import os
from flask import Flask
from threading import Thread

# ==========================================
# CHANGE THIS NUMBER TO YOUR SERVER ID
# ==========================================
MY_SERVER_ID = 123456789012345678  

app = Flask('')

@app.route('/')
def home():
    return "Speedy AI Shipboard Interface Operational."

def run_web_server():
    port = int(os.getenv("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

class SpeedyAI(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)
        
    async def setup_hook(self):
        async with aiosqlite.connect("speedy_ai.db") as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS service_records (
                    user_id INTEGER PRIMARY KEY, mid TEXT UNIQUE, joined_timestamp REAL,
                    override_duration TEXT, training_phase TEXT DEFAULT 'Phase 1', gamertag TEXT,
                    accuracy REAL DEFAULT 50.0, positioning INTEGER DEFAULT 50,
                    teamwork INTEGER DEFAULT 50, slayer_output INTEGER DEFAULT 50, comms_focus INTEGER DEFAULT 50
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS traits (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER,
                    trait_type TEXT, description TEXT, date_added TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await db.commit()
            
        guild_target = discord.Object(id=MY_SERVER_ID)
        self.tree.copy_global_to(guild=guild_target)
        await self.tree.sync(guild=guild_target)
        weekly_readiness_report.start()

bot = SpeedyAI()

def generate_mid(display_name: str) -> str:
    digits1 = f"{random.randint(100, 999)}"
    digits2 = f"{random.randint(100, 999)}"
    words = display_name.split()
    if len(words) >= 2:
        initials = f"{words[0][0]}{words[1][0]}".upper()
    elif len(words) == 1 and len(words[0]) >= 2:
        initials = f"{words[0][0]}{words[0][1]}".upper()
    else:
        initials = "ST"
    return f"{digits1}-{digits2}-{initials}"

def evaluate_tactical_patterns(kills: int, deaths: int, accuracy: float, team_avg_kd: float) -> dict:
    kd = kills / max(deaths, 1)
    stats = {"accuracy": 50, "positioning": 50, "teamwork": 50, "slayer_output": 50, "comms_focus": 50}
    directives = []

    if accuracy < 42.0:
        stats["accuracy"] = 35
        directives.append("⚠️ **[LIVE-FIRE MANDATE]**: Weapon accuracy data is suboptimal. Report to the shooting range for tracking adjustments.")
    else:
        stats["accuracy"] = 75

    if kills >= 15 and deaths >= 15:
        stats["positioning"] = 35
        stats["slayer_output"] = 70
        directives.append("🛡️ **[TACTICAL RE-ROUTE]**: High output negated by extreme casualty rates. Prioritize conservative anchoring roles.")
    elif kills < 8 and deaths >= 12:
        stats["positioning"] = 25
        stats["slayer_output"] = 30
        directives.append("👥 **[FIRETEAM COHESION CRITICAL]**: Vulnerable isolation patterns detected. Move with your team and clear corners.")
    elif kd >= 1.5 and team_avg_kd < 0.9:
        stats["slayer_output"] = 85
        stats["teamwork"] = 35
        directives.append("🤝 **[COORDINATION REQUIRED]**: Lone Wolf syndrome logged. High K/D is nullified in a loss. Anchor for your squad.")
    else:
        directives.append("🎯 **[SYSTEM NOMINAL]**: Metrics align with fleet standards. Continue routine combat rotations.")

    return {"stats": stats, "directives": "\n\n".join(directives)}

async def fetch_halo_match_metrics(gamertag: str) -> dict:
    url = f"https://halodatahive.com{gamertag}/recent_summary"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=5) as response:
                if response.status == 200:
                    data = await response.json()
                    return {
                        "kills": int(data.get("average_kills", 12)),
                        "deaths": int(data.get("average_deaths", 11)),
                        "accuracy": float(data.get("shot_accuracy", 41.5)),
                        "team_avg_kd": float(data.get("team_kd", 0.95))
                    }
    except Exception:
        pass
    return {"kills": 14, "deaths": 15, "accuracy": 39.8, "team_avg_kd": 0.85}

def is_sergeant_plus():
    async def predicate(interaction: discord.Interaction) -> bool:
        allowed_roles = ["Sergeant", "Lieutenant", "Captain", "Admin", "Staff"]
        has_role = any(role.name in allowed_roles for role in interaction.user.roles)
        if has_role or interaction.user.guild_permissions.administrator:
            return True
        await interaction.response.send_message("❌ [ACCESS DENIED]: Clearance tier 'Sergeant' or higher required.", ephemeral=True)
        return False
    return app_commands.check(predicate)

@bot.event
async def on_ready():
    print(f"🤖 Connected successfully as: {bot.user}")

@bot.event
async def on_member_update(before, after):
    odst_role_name = "O.D.S.T"
    had_role = any(r.name == odst_role_name for r in before.roles)
    has_role = any(r.name == odst_role_name for r in after.roles)
    
    if not had_role and has_role:
        mid = generate_mid(after.display_name)
        async with aiosqlite.connect("speedy_ai.db") as db:
            async with db.execute("SELECT user_id FROM service_records WHERE user_id = ?", (after.id,)) as cursor:
                if await cursor.fetchone() is None:
                    await db.execute("INSERT INTO service_records (user_id, mid, joined_timestamp) VALUES (?, ?, ?)", (after.id, mid, time.time()))
                    await db.commit()

@bot.tree.command(name="service_record", description="Review an ODST's core service history and tactical diagnostics.")
async def service_record(interaction: discord.Interaction, member: discord.Member = None):
    target = member or interaction.user
    async with aiosqlite.connect("speedy_ai.db") as db:
        async with db.execute("SELECT * FROM service_records WHERE user_id = ?", (target.id,)) as cursor:
            row = await cursor.fetchone()
            if not row:
                await interaction.response.send_message("📁 Profile uninitialized. Target must possess the O.D.S.T role.", ephemeral=True)
                return
            
            user_id, mid, joined_time, override_duration, phase, gamertag, acc, pos, team, slay, comms = row
            
            if override_duration:
                time_in_service = override_duration
            else:
                elapsed = time.time() - joined_time
                months, days = int(elapsed // 2592000), int((elapsed % 2592000) // 86400)
                time_in_service = f"{months} Months, {days} Days"

            if gamertag:
                await interaction.response.defer()
                metrics = await fetch_halo_match_metrics(gamertag)
            else:
                metrics = {"kills": 10, "deaths": 10, "accuracy": 45.0, "team_avg_kd": 1.0}

            analysis = evaluate_tactical_patterns(metrics["kills"], metrics["deaths"], metrics["accuracy"], metrics["team_avg_kd"])

            embed = discord.Embed(title=f"🪖 SERVICE RECORD // {target.display_name.upper()}", color=0x2ecc71)
            embed.add_field(name="🆔 Marine ID", value=f"`{mid}`", inline=True)
            embed.add_field(name="⏳ Time in Service", value=time_in_service, inline=True)
            embed.add_field(name="📈 Phase", value=f"`{phase}`", inline=True)
            embed.add_field(name="🎮 Linked Gamertag", value=f"`{gamertag or 'UNLINKED'}`", inline=True)
            
            stats_block = f"🎯 Accuracy: `{analysis['stats']['accuracy']}/100`\n🗺️ Positioning: `{analysis['stats']['positioning']}/100`\n🤝 Teamwork: `{analysis['stats']['teamwork']}/100`"
            embed.add_field(name="📊 Attributes", value=stats_block, inline=False)
            embed.add_field(name="🧠 Speedy's Pattern Assessment", value=analysis["directives"], inline=False)
            embed.set_footer(text="Speedy AI Shipboard Interface • Live Manifest V2.5")
            
            if gamertag:
                await interaction.followup.send(embed=embed)
            else:
                await interaction.response.send_message(embed=embed)

@bot.tree.command(name="register_gamertag", description="Link your Xbox Live Gamertag to your ODST Service Record.")
async def register_gamertag(interaction: discord.Interaction, gamertag: str):
    user = interaction.user
    async with aiosqlite.connect("speedy_ai.db") as db:
        async with db.execute("SELECT user_id FROM service_records WHERE user_id = ?", (user.id,)) as cursor:
            if await cursor.fetchone() is None:
                await interaction.response.send_message("❌ [ACCESS DENIED]: Profile uninitialized. Missing O.D.S.T assignment.", ephemeral=True)
                return
        await db.execute("UPDATE service_records SET gamertag = ? WHERE user_id = ?", (gamertag, user.id))
        await db.commit()
    await interaction.response.send_message(f"📡 **[LINK ESTABLISHED]**: Gamertag `{gamertag}` synced to data channels.", ephemeral=True)

@bot.tree.command(name="service_record_override", description="Override parameters (Requires Sergeant Clearance).")
@is_sergeant_plus()
async def service_record_override(interaction: discord.Interaction, member: discord.Member, new_time: str = None, phase: str = None, gamertag: str = None):
    async with aiosqlite.connect("speedy_ai.db") as db:
        if new_time:
            await db.execute("UPDATE service_records SET override_duration = ? WHERE user_id = ?", (new_time, member.id))
