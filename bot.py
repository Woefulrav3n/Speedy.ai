import discord
from discord import app_commands
from discord.ext import commands, tasks
import random
import time
import aiosqlite
import aiohttp
import os
from datetime import datetime
from flask import Flask
from threading import Thread

# ==========================================
# 🌐 1. DETACHED 24/7 FREE HOSTING KEEP-ALIVE
# ==========================================
app = Flask('')

@app.route('/')
def home():
    return "Speedy AI Shipboard Interface Operational."

def run_web_server():
    # Flask runs on port 8080 so Render can ping it to stay awake for free
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    """Spins up a lightweight background web server thread."""
    t = Thread(target=run_web_server)
    t.start()


# ==========================================
# 🤖 2. BOT CORE INITIALIZATION & SETUP
# ==========================================
intents = discord.Intents.default()
intents.members = True
intents.message_content = True

class SpeedyAI(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)
        
    async def setup_hook(self):
        # Dynamically create the database tables if they do not exist
        async with aiosqlite.connect("speedy_ai.db") as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS service_records (
                    user_id INTEGER PRIMARY KEY, 
                    mid TEXT UNIQUE, 
                    joined_timestamp REAL,
                    override_duration TEXT, 
                    training_phase TEXT DEFAULT 'Phase 1', 
                    gamertag TEXT,
                    accuracy REAL DEFAULT 50.0, 
                    positioning INTEGER DEFAULT 50,
                    teamwork INTEGER DEFAULT 50, 
                    slayer_output INTEGER DEFAULT 50, 
                    comms_focus INTEGER DEFAULT 50
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS traits (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, 
                    user_id INTEGER,
                    trait_type TEXT, 
                    description TEXT, 
                    date_added TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await db.commit()
            
        # Start the background weekly assessment cycle automatically
        weekly_readiness_report.start()
        
        # Sync slash commands with Discord
        await self.tree.sync()

bot = SpeedyAI()


# ==========================================
# 🧠 3. PATTERN-MATCHING & API LOGIC ENGINES
# ==========================================
def generate_mid(display_name: str) -> str:
    """Generates a Marine Identification Number: XXX-XXX-XX (Random digits + Initials)."""
    digits1 = f"{random.randint(100, 999)}"
    digits2 = f"{random.randint(100, 999)}"
    words = display_name.split()
    if len(words) >= 2:
        initials = f"{words[0][0]}{words[1][0]}".upper()
    elif len(words) == 1 and len(words[0]) >= 2:
        initials = f"{words[0][0]}{words[0][1]}".upper()
    else:
        initials = "ST"  # Shock Trooper default fallback
    return f"{digits1}-{digits2}-{initials}"

def evaluate_tactical_patterns(kills: int, deaths: int, accuracy: float, team_avg_kd: float) -> dict:
    """Speedy's calculated pattern-matching analytical engine."""
    kd = kills / max(deaths, 1)
    stats = {"accuracy": 50, "positioning": 50, "teamwork": 50, "slayer_output": 50, "comms_focus": 50}
    directives = []
    faults = []
    skills = []

    # Pattern 1: Below competitive accuracy standards
    if accuracy < 42.0:
        stats["accuracy"] = 35
        faults.append("Erratic Weapon Tracking")
        directives.append("⚠️ **[LIVE-FIRE MANDATE]**: Marksmanship yields poor groupings. Report to the live-fire shooting range immediately for weapon pacing drills and tracking adjustments.")
    else:
        stats["accuracy"] = 75
        skills.append("Precise Marksmanship")

    # Pattern 2: High Kills / High Deaths (Aggressive trading)
    if kills >= 15 and deaths >= 15:
        stats["positioning"] = 35
        stats["slayer_output"] = 70
        faults.append("Over-Aggressive Exposure")
        directives.append("🛡️ **[TACTICAL RE-ROUTE]**: High casualty rate negates high kill counts. Prioritize conservative playstyles, anchor map spawns, and switch to a supporting role to preserve team lives.")
    
    # Pattern 3: Low Kills / High Deaths (Struggling/Isolated asset)
    elif kills < 8 and deaths >= 12:
        stats["positioning"] = 25
        stats["slayer_output"] = 30
        faults.append("Vulnerable Isolation")
        directives.append("👥 **[FIRETEAM COHESION CRITICAL]**: High vulnerability recorded. Stick closely with your fireteam, advance cleanly, and check corners thoroughly before exposing sightlines.")
    
    # Pattern 4: Lone Wolf syndrome
    elif kd >= 1.5 and team_avg_kd < 0.9:
        stats["slayer_output"] = 85
        stats["teamwork"] = 35
        skills.append("High Combat Efficiency")
        faults.append("Lone Wolf Behavioral Tendencies")
        directives.append("🤝 **[COORDINATION REQUIRED]**: Exceptional personal output, but your squad is bleeding out. High K/D is nullified in a match loss. Shift targets to protect and cover your fireteam.")
    
    # Pattern 5: Optimum performance
    else:
        directives.append("🎯 **[SYSTEM NOMINAL]**: General metrics balanced. Continue routine tactical training deployments and maintain standard communications.")

    return {"stats": stats, "directives": "\n\n".join(directives), "skills": skills, "faults": faults}

async def fetch_halo_match_metrics(gamertag: str) -> dict:
    """Asynchronously pulls active match statistics from free community API endpoints."""
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
    
    # Safe fallback template values so Speedy never crashes if external services go offline
    return {"kills": 13, "deaths": 14, "accuracy": 39.5, "team_avg_kd": 0.85}


# ==========================================
# 🔒 4. SECURITY & CLEARANCE PERMISSIONS
# ==========================================
def is_sergeant_plus():
    """Restricts execution strictly to users holding Sergeant+ or Admin roles."""
    async def predicate(interaction: discord.Interaction) -> bool:
        allowed_roles = ["Sergeant", "Lieutenant", "Captain", "Admin", "Staff", "Master Sergeant"]
        has_role = any(role.name in allowed_roles for role in interaction.user.roles)
        if has_role or interaction.user.guild_permissions.administrator:
            return True
        await interaction.response.send_message("❌ [ACCESS DENIED]: Clearance Sergeant or higher required.", ephemeral=True)
        return False
    return app_commands.check(predicate)


# ==========================================
# 🎛️ 5. INTERFACE COMMANDS & USER INTERACTION
# ==========================================
@bot.event
async def on_member_update(before, after):
    """Automatically assigns an M.I.D profile when an asset receives the O.D.S.T role."""
    odst_role_name = "O.D.S.T"
    had_role = any(r.name == odst_role_name for r in before.roles)
    has_role = any(r.name == odst_role_name for r in after.roles)
    
    if not had_role and has_role:
        mid = generate_mid(after.display_name)
        async with aiosqlite.connect("speedy_ai.db") as db:
            async with db.execute("SELECT user_id FROM service_records WHERE user_id = ?", (after.id,)) as cursor:
                if await cursor.fetchone() is None:
                    await db.execute("""
                        INSERT INTO service_records (user_id, mid, joined_timestamp) 
                        VALUES (?, ?, ?)
                    """, (after.id, mid, time.time()))
                    await db.commit()

@bot.tree.command(name="register_gamertag", description="Link your Xbox Live Gamertag to your ODST Service Record.")
async def register_gamertag(interaction: discord.Interaction, gamertag: str):
    user = interaction.user
    async with aiosqlite.connect("speedy_ai.db") as db:
        async with db.execute("SELECT user_id FROM service_records WHERE user_id = ?", (user.id,)) as cursor:
            if await cursor.fetchone() is None:
                await interaction.response.send_message("❌ [ACCESS DENIED]: Profile uninitialized. You must hold the O.D.S.T role.", ephemeral=True)
                return
        await db.execute("UPDATE service_records SET gamertag = ? WHERE user_id = ?", (gamertag, user.id))
        await db.commit()
    await interaction.response.send_message(f"📡 **[LINK CONFIRMED]**: Xbox Live Gamertag `{gamertag}` locked to manifest.", ephemeral=True)

@bot.tree.command(name="service_record", description="Review an ODST's core service history and tactical diagnostics.")
async def service_record(interaction: discord.Interaction, member: discord.Member = None):
    target = member or interaction.user
    
    async with aiosqlite.connect("speedy_ai.db") as db:
        async with db.execute("SELECT * FROM service_records WHERE user_id = ?", (target.id,)) as cursor:
            row = await cursor.fetchone()
            if not row:
