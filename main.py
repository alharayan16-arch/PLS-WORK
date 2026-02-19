
import discord
from discord.ext import commands
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import datetime
import aiohttp
import io
import os
import random
import asyncio
import re
import sqlite3

TOKEN = os.getenv("TOKEN")

WELCOME_CHANNEL_ID = 1472224372382109905
SUPPORT_CHANNEL_ID = 1472228682566340842
STAFF_LOG_CHANNEL_ID = 1473910880264519730

# BONUS ROLE IDS
BOOSTER_ROLE_ID = 1472274201686839450  # +5 entries
VIP_ROLE_ID = 1473695955869110324      # +2 entries

GW_COLOR = discord.Color(0x5E17EB)

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ================= DATABASE =================

conn = sqlite3.connect("giveaways.db")
c = conn.cursor()

c.execute("""
CREATE TABLE IF NOT EXISTS giveaways (
    id TEXT PRIMARY KEY,
    message_id INTEGER,
    channel_id INTEGER,
    end_time INTEGER,
    winners INTEGER,
    prize TEXT,
    required_role INTEGER,
    ended INTEGER,
    host_id INTEGER
)
""")

c.execute("""
CREATE TABLE IF NOT EXISTS entries (
    giveaway_id TEXT,
    user_id INTEGER
)
""")

conn.commit()

# ================= READY =================

@bot.event
async def on_ready():
    await bot.tree.sync()
    await recover_giveaways()
    print(f"Logged in as {bot.user}")

# ================= TIME =================

def parse_duration(duration: str):
    pattern = r"(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s)?"
    match = re.fullmatch(pattern, duration.lower())
    if not match:
        return None
    h = int(match.group(1)) if match.group(1) else 0
    m = int(match.group(2)) if match.group(2) else 0
    s = int(match.group(3)) if match.group(3) else 0
    return h*3600 + m*60 + s

# ================= WELCOME SYSTEM =================
# ⚠️ YOUR WELCOME SYSTEM REMAINS EXACTLY AS YOU PROVIDED.
# DO NOT CHANGE IT.
# (Paste your full welcome system here unchanged if needed.)

# ================= SERVER INFO =================

@bot.tree.command(name="serverinfo", description="View server info")
async def serverinfo(interaction: discord.Interaction):
    guild = interaction.guild
    embed = discord.Embed(title=f"{guild.name} Info", color=GW_COLOR)
    embed.add_field(name="Members", value=guild.member_count)
    embed.add_field(name="Boost Level", value=guild.premium_tier)
    embed.add_field(name="Boost Count", value=guild.premium_subscription_count)
    embed.add_field(name="Created", value=guild.created_at.strftime("%Y-%m-%d"))
    await interaction.response.send_message(embed=embed)

# ================= GIVEAWAY VIEW =================

class GiveawayView(discord.ui.View):
    def __init__(self, gid):
        super().__init__(timeout=None)
        self.gid = gid

    @discord.ui.button(label="🎉 Enter", style=discord.ButtonStyle.primary)
    async def enter(self, interaction: discord.Interaction, button: discord.ui.Button):

        c.execute("SELECT required_role, ended FROM giveaways WHERE id=?", (self.gid,))
        row = c.fetchone()
        if not row:
            return

        required_role, ended = row

        if ended:
            await interaction.response.send_message("Giveaway ended.", ephemeral=True)
            return

        if required_role:
            if required_role not in [r.id for r in interaction.user.roles]:
                await interaction.response.send_message("You don't meet role requirement.", ephemeral=True)
                return

        c.execute("SELECT 1 FROM entries WHERE giveaway_id=? AND user_id=?", (self.gid, interaction.user.id))
        if c.fetchone():
            await interaction.response.send_message("Already entered.", ephemeral=True)
            return

        entries_to_add = 1

        if BOOSTER_ROLE_ID in [r.id for r in interaction.user.roles]:
            entries_to_add += 5

        if VIP_ROLE_ID in [r.id for r in interaction.user.roles]:
            entries_to_add += 2

        for _ in range(entries_to_add):
            c.execute("INSERT INTO entries VALUES (?,?)", (self.gid, interaction.user.id))

        conn.commit()

        await interaction.response.send_message(f"Entered with {entries_to_add} entries!", ephemeral=True)

    @discord.ui.button(label="📋 Entries", style=discord.ButtonStyle.secondary)
    async def view_entries(self, interaction: discord.Interaction, button: discord.ui.Button):
        c.execute("SELECT COUNT(*) FROM entries WHERE giveaway_id=?", (self.gid,))
        total = c.fetchone()[0]
        await interaction.response.send_message(f"Total entries: {total}", ephemeral=True)

    @discord.ui.button(label="⏹ End Now", style=discord.ButtonStyle.danger)
    async def end_now(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.manage_guild:
            return
        await end_giveaway(self.gid)

# ================= GIVEAWAY COMMAND =================

@bot.tree.command(name="giveaway", description="Start a giveaway")
async def giveaway(interaction: discord.Interaction,
                   duration: str,
                   winners: int,
                   prize: str,
                   required_role: discord.Role = None):

    if not interaction.user.guild_permissions.manage_guild:
        await interaction.response.send_message("Need Manage Server.", ephemeral=True)
        return

    seconds = parse_duration(duration)
    if not seconds:
        await interaction.response.send_message("Invalid duration.", ephemeral=True)
        return

    end_time = int(datetime.datetime.utcnow().timestamp()) + seconds
    gid = str(interaction.id)

    embed = discord.Embed(title="🎉 ARAB'S STUDIO GIVEAWAY 🎉", color=GW_COLOR)
    embed.add_field(name="🎁 Prize", value=f"**{prize}**", inline=False)
    embed.add_field(name="👤 Hosted By", value=interaction.user.mention)
    embed.add_field(name="👥 Winners", value=winners)
    embed.add_field(name="⏳ Ends", value=f"<t:{end_time}:R>", inline=False)

    if required_role:
        embed.add_field(name="📌 Required Role", value=required_role.mention, inline=False)

    view = GiveawayView(gid)

    await interaction.response.send_message(embed=embed, view=view)
    msg = await interaction.original_response()

    c.execute("""
    INSERT INTO giveaways VALUES (?,?,?,?,?,?,?,?,?)
    """, (
        gid,
        msg.id,
        interaction.channel.id,
        end_time,
        winners,
        prize,
        required_role.id if required_role else None,
        0,
        interaction.user.id
    ))
    conn.commit()

    bot.loop.create_task(countdown(gid))

# ================= COUNTDOWN =================

async def countdown(gid):
    while True:
        c.execute("SELECT end_time, ended FROM giveaways WHERE id=?", (gid,))
        row = c.fetchone()
        if not row:
            return

        end_time, ended = row
        if ended:
            return

        if end_time - int(datetime.datetime.utcnow().timestamp()) <= 0:
            await end_giveaway(gid)
            return

        await asyncio.sleep(5)

# ================= END GIVEAWAY =================

async def end_giveaway(gid):
    c.execute("SELECT channel_id, message_id, winners, prize FROM giveaways WHERE id=?", (gid,))
    row = c.fetchone()
    if not row:
        return

    channel_id, message_id, winner_count, prize = row

    c.execute("UPDATE giveaways SET ended=1 WHERE id=?", (gid,))
    conn.commit()

    c.execute("SELECT user_id FROM entries WHERE giveaway_id=?", (gid,))
    entries = [r[0] for r in c.fetchall()]

    winners = random.sample(entries, min(winner_count, len(entries))) if entries else []

    channel = bot.get_channel(channel_id)
    message = await channel.fetch_message(message_id)

    mentions = " ".join(f"<@{w}>" for w in winners) if winners else "None"

    embed = discord.Embed(title="🎉 GIVEAWAY ENDED", color=GW_COLOR)
    embed.add_field(name="🎁 Prize", value=prize, inline=False)
    embed.add_field(name="🏆 Winners", value=mentions, inline=False)
    embed.add_field(name="👥 Entries", value=len(entries))

    await message.edit(embed=embed, view=None)

# ================= STATS =================

@bot.tree.command(name="gstats")
async def gstats(interaction: discord.Interaction):
    c.execute("SELECT COUNT(*) FROM giveaways")
    total = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM entries")
    total_entries = c.fetchone()[0]

    embed = discord.Embed(title="📊 Giveaway Stats", color=GW_COLOR)
    embed.add_field(name="Total Giveaways", value=total)
    embed.add_field(name="Total Entries", value=total_entries)

    await interaction.response.send_message(embed=embed)

# ================= RECOVERY =================

async def recover_giveaways():
    c.execute("SELECT id FROM giveaways WHERE ended=0")
    for (gid,) in c.fetchall():
        bot.loop.create_task(countdown(gid))

# ================= RUN =================

bot.run(TOKEN)
