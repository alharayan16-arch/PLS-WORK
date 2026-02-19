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

BOOSTER_ROLE_ID = 1472274201686839450  # +5
VIP_ROLE_ID = 1473695955869110324      # +2

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

# ================= SHARED ANIMATION BASE =================

def generate_base_background(width, height):
    base_bg = Image.new("RGB", (width, height))
    bg_draw = ImageDraw.Draw(base_bg)
    for y in range(height):
        for x in range(width):
            ratio = (x + y) / (width + height)
            r = int(55 - ratio * 30)
            g = 0
            b = int(105 - ratio * 50)
            bg_draw.point((x, y), fill=(r, g, b))
    return base_bg.convert("RGBA")

def add_pattern(img, font_small, frame, spacing=60):
    width, height = img.size
    pattern_layer = Image.new("RGBA", (width * 2, height), (0, 0, 0, 0))
    p_draw = ImageDraw.Draw(pattern_layer)

    for y in range(0, height, spacing):
        for x in range(0, width * 2, spacing):
            p_draw.text((x, y), "X", font=font_small, fill=(255, 255, 255, 50))
            p_draw.text((x + 25, y + 25), "O", font=font_small, fill=(255, 255, 255, 50))

    offset = (frame * 4) % spacing
    cropped = pattern_layer.crop((offset, 0, offset + width, height))
    return Image.alpha_composite(img, cropped)

# ================= WELCOME GIF =================

async def create_welcome_gif(member):

    width, height = 1000, 400
    frames = []

    font_title = ImageFont.truetype("Montserrat-Bold.ttf", 70)
    font_user = ImageFont.truetype("Montserrat-Regular.ttf", 40)
    font_small = ImageFont.truetype("Montserrat-Regular.ttf", 28)

    sequence = ["W","WE","WEL","WELC","WELCO","WELCOM","WELCOME"]

    base_bg = generate_base_background(width, height)

    async with aiohttp.ClientSession() as session:
        async with session.get(member.display_avatar.url) as resp:
            avatar_bytes = await resp.read()

    avatar = Image.open(io.BytesIO(avatar_bytes)).convert("RGBA")
    avatar = avatar.resize((110, 110))
    mask = Image.new("L", (110, 110), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, 110, 110), fill=255)
    avatar.putalpha(mask)

    total_frames = len(sequence) * 6 + 20

    for frame in range(total_frames):
        img = base_bg.copy()
        img = add_pattern(img, font_small, frame)
        draw = ImageDraw.Draw(img)

        index = min(len(sequence)-1, frame // 6)
        title_text = sequence[index]

        draw.text((60, 60), title_text, font=font_title, fill=(255,255,255))
        draw.text((200, 150), member.display_name, font=font_user, fill=(255,255,255))

        img.paste(avatar, (60, 150), avatar)

        frames.append(img)

    path = f"welcome_{member.id}.gif"
    frames[0].save(path, save_all=True, append_images=frames[1:], duration=60, loop=0)
    return path

@bot.event
async def on_member_join(member):
    channel = bot.get_channel(WELCOME_CHANNEL_ID)
    gif = await create_welcome_gif(member)
    await channel.send(
        content=f"{member.mention}, Welcome to Arab’s Studio — we’re glad to have you here!",
        file=discord.File(gif)
    )

# ================= GIVEAWAY GIF =================

async def create_giveaway_gif(prize_text):

    width, height = 1000, 400
    frames = []

    font_title = ImageFont.truetype("Montserrat-Bold.ttf", 90)
    font_prize = ImageFont.truetype("Montserrat-Regular.ttf", 45)
    font_small = ImageFont.truetype("Montserrat-Regular.ttf", 28)

    sequence = ["G","GI","GIV","GIVE","GIVEA","GIVEAW","GIVEAWA","GIVEAWAY"]

    base_bg = generate_base_background(width, height)
    total_frames = len(sequence) * 6 + 20

    for frame in range(total_frames):
        img = base_bg.copy()
        img = add_pattern(img, font_small, frame)
        draw = ImageDraw.Draw(img)

        index = min(len(sequence)-1, frame // 6)
        title_text = sequence[index]

        title_w = draw.textlength(title_text, font=font_title)
        draw.text(((width-title_w)/2, 100), title_text, font=font_title, fill=(255,255,255))

        prize_w = draw.textlength(prize_text, font=font_prize)
        draw.text(((width-prize_w)/2, 220), prize_text, font=font_prize, fill=(230,230,255))

        frames.append(img)

    path = f"giveaway_{random.randint(1,999999)}.gif"
    frames[0].save(path, save_all=True, append_images=frames[1:], duration=60, loop=0)
    return path

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

        if required_role and required_role not in [r.id for r in interaction.user.roles]:
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

        # Live update embed entry count
        c.execute("SELECT COUNT(*) FROM entries WHERE giveaway_id=?", (self.gid,))
        total_entries = c.fetchone()[0]

        message = interaction.message
        embed = message.embeds[0]

        for i, field in enumerate(embed.fields):
            if field.name == "🎟 Entries":
                embed.remove_field(i)
                break

        embed.add_field(name="🎟 Entries", value=str(total_entries), inline=True)
        await message.edit(embed=embed, view=self)

        await interaction.response.send_message(
            f"Entered with {entries_to_add} entries!",
            ephemeral=True
        )

    @discord.ui.button(label="⏹ End Now", style=discord.ButtonStyle.danger)
    async def end_now(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.manage_guild:
            return
        await end_giveaway(self.gid)

# ================= GIVEAWAY COMMAND =================

@bot.tree.command(name="giveaway")
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

    gif_path = await create_giveaway_gif(prize)
    file = discord.File(gif_path)
    
    embed = discord.Embed(title="🎉 ARAB'S STUDIO GIVEAWAY 🎉", color=GW_COLOR)
    embed.set_image(url=f"attachment://{os.path.basename(gif_path)}")
    embed.add_field(name="🎁 Prize", value=f"**{prize}**", inline=False)
    embed.add_field(name="👤 Hosted By", value=interaction.user.mention)
    embed.add_field(name="👥 Winners", value=winners)
    embed.add_field(name="⏳ Ends", value=f"<t:{end_time}:R>", inline=False)
    embed.add_field(name="🎟 Entries", value="0", inline=True)

    if required_role:
        embed.add_field(name="📌 Required Role", value=required_role.mention, inline=False)

    view = GiveawayView(gid)

    await interaction.response.send_message(embed=embed, view=view, file=file)
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
