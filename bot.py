import discord
from discord import app_commands
from discord.ext import commands, tasks
import os
import random
import time
import aiosqlite
import aiohttp
from flask import Flask
from threading import Thread

# ==========================================
# CHANGE THIS NUMBER TO YOUR SERVER ID
# ==========================================
MY_SERVER_ID = 1547705148355248200  

app = Flask('')

@app.route('/')
def home():
    return "Speedy AI Operational."

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
    initials = "".join([w[0] for w in words[:2]]).upper() if len(words) >= 1 else "ST"
    return f"{digits1}-{digits2}-{initials}"

def evaluate_tactical_patterns(kills: int, deaths: int, accuracy: float, team_avg_kd: float) -> dict:
    kd = kills / max(deaths, 1)
    stats = {"accuracy": 50, "positioning": 50, "teamwork": 50}
    directives = []

    if accuracy < 42.0:
        stats["accuracy"] = 35
        directives.append("⚠️ **[LIVE-FIRE MANDATE]**: Accuracy low. Report to the shooting range for tracking drills.")
    else:
        stats["accuracy"] = 75

    if kills >= 15 and deaths >= 15:
        stats["positioning"] = 35
        directives.append("🛡️ **[TACTICAL RE-ROUTE]**: High output negated by high deaths. Switch to conservative anchoring.")
    elif kills < 8 and deaths >= 12:
        stats["positioning"] = 25
        directives.append("👥 **[FIRETEAM COHESION CRITICAL]**: Vulnerable isolation. Move with team and clear corners.")
    elif kd >= 1.5 and team_avg_kd < 0.9:
        stats["teamwork"] = 35
        directives.append("🤝 **[COORDINATION REQUIRED]**: Lone Wolf habits. Assist struggling squad mates.")
    else:
        directives.append("🎯 **[SYSTEM NOMINAL]**: Metrics align with fleet standards. Maintain current rotation.")

    return {"stats": stats, "directives": "\n\n".join(directives)}

async def fetch_halo_match_metrics(gamertag: str) -> dict:
    url = f"https://halodatahive.com{gamertag}/recent_summary"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=5) as response:
                if response.status == 200:
                    data = await response.json()
                    return {
                        "kills": int(data.get("average_kills", 12)), "deaths": int(data.get("average_deaths", 11)),
                        "accuracy": float(data.get("shot_accuracy", 41.5)), "team_avg_kd": float(data.get("team_kd", 0.95))
                    }
    except:
        pass
    return {"kills": 14, "deaths": 15, "accuracy": 39.8, "team_avg_kd": 0.85}

def is_sergeant_plus():
    async def predicate(interaction: discord.Interaction) -> bool:
        allowed = ["Sergeant", "Lieutenant", "Captain", "Admin", "Staff"]
        if any(r.name in allowed for r in interaction.user.roles) or interaction.user.guild_permissions.administrator:
            return True
        await interaction.response.send_message("❌ [ACCESS DENIED]: Requires Sergeant clearance.", ephemeral=True)
        return False
    return app_commands.check(predicate)

