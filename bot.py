import discord
from discord import app_commands
from discord.ext import commands, tasks
import os
import time
import random
import aiosqlite
from flask import Flask
from threading import Thread

# ==========================================
# 🛑 PUT YOUR EXACT DISCORD SERVER ID HERE
# ==========================================
MY_SERVER_ID = 1547705148355248200  

app = Flask('')

@app.route('/')
def home():
    return "Speedy AI Operational."

def run_web_server():
    port = int(os.getenv("PORT", 10000))
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
                    override_duration TEXT, training_phase TEXT DEFAULT 'Phase 1', gamertag TEXT
                )
            """)
            await db.commit()
            
        guild_target = discord.Object(id=MY_SERVER_ID)
        self.tree.copy_global_to(guild=guild_target)
        await self.tree.sync(guild=guild_target)

bot = SpeedyAI()

@bot.event
async def on_ready():
    print(f"🤖 Speedy connected as: {bot.user}")

@bot.event
async def on_member_update(before, after):
    odst_role = "O.D.S.T"
    if not any(r.name == odst_role for r in before.roles) and any(r.name == odst_role for r in after.roles):
        digits1 = random.randint(100, 999)
        digits2 = random.randint(100, 999)
        words = after.display_name.split()
        initials = "".join([w[0] for w in words[:2]]).upper() if len(words) >= 1 else "ST"
        mid = f"{digits1}-{digits2}-{initials}"
        
        async with aiosqlite.connect("speedy_ai.db") as db:
            await db.execute("INSERT OR IGNORE INTO service_records (user_id, mid, joined_timestamp) VALUES (?, ?, ?)", (after.id, mid, time.time()))
            await db.commit()

@bot.tree.command(name="service_record", description="Review an ODST history profile.")
async def service_record(interaction: discord.Interaction, member: discord.Member = None):
    target = member or interaction.user
    async with aiosqlite.connect("speedy_ai.db") as db:
        async with db.execute("SELECT * FROM service_records WHERE user_id = ?", (target.id,)) as cursor:
            row = await cursor.fetchone()
            
    if not row:
        await interaction.response.send_message("📁 No profile found. User must have the O.D.S.T role.", ephemeral=True)
        return
        
    user_id, mid, joined_time, override_duration, phase, gamertag = row
    time_str = override_duration if override_duration else f"{int((time.time() - joined_time) // 2592000)} Months"
    
    embed = discord.Embed(title=f"🪖 ODST PROFILE // {target.display_name.upper()}", color=0x3498db)
    embed.add_field(name="🆔 Marine ID", value=f"`{mid}`", inline=True)
    embed.add_field(name="⏳ Time in Service", value=time_str, inline=True)
    embed.add_field(name="📈 Status", value=f"`{phase}`", inline=True)
    embed.add_field(name="🎮 Gamertag", value=f"`{gamertag or 'UNLINKED'}`", inline=True)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="register_gamertag", description="Link your Xbox Live Gamertag.")
async def register_gamertag(interaction: discord.Interaction, gamertag: str):
    async with aiosqlite.connect("speedy_ai.db") as db:
        await db.execute("UPDATE service_records SET gamertag = ? WHERE user_id = ?", (gamertag, interaction.user.id))
        await db.commit()
    await interaction.response.send_message(f"📡 Syncing complete for gamertag: `{gamertag}`.", ephemeral=True)

@bot.tree.command(name="service_record_override", description="Override record attributes.")
async def service_record_override(interaction: discord.Interaction, member: discord.Member, new_time: str = None, phase: str = None):
    allowed_roles = ["Sergeant", "Lieutenant", "Captain", "Admin", "Staff"]
    if not any(r.name in allowed_roles for r in interaction.user.roles) and not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ [ACCESS DENIED]: Clearance Sergeant required.", ephemeral=True)
        return
        
    async with aiosqlite.connect("speedy_ai.db") as db:
        if new_time:
            await db.execute("UPDATE service_records SET override_duration = ? WHERE user_id = ?", (new_time, member.id))
        if phase:
            await db.execute("UPDATE service_records SET training_phase = ? WHERE user_id = ?", (phase, member.id))
        await db.commit()
    await interaction.response.send_message(f"✅ Record updated successfully for {member.display_name}.", ephemeral=True)

if __name__ == "__main__":
    TOKEN = os.getenv("DISCORD_TOKEN")
    if TOKEN:
        t = Thread(target=run_web_server)
        t.daemon = True
        t.start()
        bot.run(TOKEN)
    else:
        print("❌ CRITICAL ERROR: DISCORD_TOKEN variable missing.")
