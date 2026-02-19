import discord
from discord.ext import commands
from PIL import Image, ImageDraw, ImageFont
import aiohttp
import asyncio
import datetime
import io
import os
import random
import re
import sqlite3

print("MAIN FILE STARTED")

TOKEN = os.getenv("TOKEN")

if not TOKEN:
    raise RuntimeError("TOKEN environment variable is missing!")

WELCOME_CHANNEL_ID = 1472224372382109905
BOOSTER_ROLE_ID = 1472274201686839450
VIP_ROLE_ID = 1473695955869110324

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
    ended INTEGER
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
    print("BOT LOGGED IN:", bot.user)
    await bot.tree.sync()
    await recover_giveaways()

# ================= UTIL =================

def parse_duration(duration):
    pattern = r"(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s)?"
    match = re.fullmatch(pattern, duration.lower())
    if not match:
        return None
    h = int(match.group(1)) if match.group(1) else 0
    m = int(match.group(2)) if match.group(2) else 0
    s = int(match.group(3)) if match.group(3) else 0
    return h*3600 + m*60 + s

# ================= SIMPLE BACKGROUND =================

def generate_background(width, height):
    img = Image.new("RGB", (width, height))
    draw = ImageDraw.Draw(img)
    for y in range(height):
        for x in range(width):
            ratio = (x+y)/(width+height)
            draw.point((x,y), fill=(int(55-ratio*30),0,int(105-ratio*50)))
    return img

# ================= WELCOME GIF =================

async def create_giveaway_gif(prize):
    width, height = 800, 300
    frames = []

    font_big = ImageFont.truetype("Montserrat-Bold.ttf", 70)
    font_small = ImageFont.truetype("Montserrat-Regular.ttf", 28)
    font_prize = ImageFont.truetype("Montserrat-Regular.ttf", 40)
    font_logo = ImageFont.truetype("Montserrat-Bold.ttf", 90)

    sequence = ["G","GI","GIV","GIVE","GIVEA","GIVEAW","GIVEAWA","GIVEAWAY"]

    base_bg = generate_background(width, height)

    spacing = 60
    typing_speed = 5
    total_frames = len(sequence) * typing_speed + 30

    for frame in range(total_frames):

        img = base_bg.copy()

        # ===== MOVING X O PATTERN =====
        pattern_layer = Image.new("RGBA", (width * 2, height), (0, 0, 0, 0))
        p_draw = ImageDraw.Draw(pattern_layer)

        for y in range(0, height, spacing):
            for x in range(0, width * 2, spacing):
                p_draw.text((x, y), "X", font=font_small, fill=(255,255,255,50))
                p_draw.text((x+25, y+25), "O", font=font_small, fill=(255,255,255,50))

        offset = (frame * 4) % spacing
        cropped = pattern_layer.crop((offset, 0, offset + width, height))
        img = Image.alpha_composite(img.convert("RGBA"), cropped)

        draw = ImageDraw.Draw(img)

        # ===== TYPING =====
        text = sequence[min(len(sequence)-1, frame // typing_speed)]

        tw = draw.textlength(text, font=font_big)
        text_x = (width - tw) / 2
        text_y = 50

        draw.text((text_x, text_y), text, font=font_big, fill=(255,255,255))

        # ===== SHINE SWEEP =====
        shine_layer = Image.new("RGBA", img.size, (0,0,0,0))
        shine_draw = ImageDraw.Draw(shine_layer)

        shine_x = (frame * 20) % (width + 200) - 200
        shine_draw.rectangle(
            [shine_x, text_y-10, shine_x+80, text_y+90],
            fill=(255,255,255,60)
        )

        img = Image.alpha_composite(img, shine_layer)

        draw = ImageDraw.Draw(img)

        # ===== PRIZE =====
        pw = draw.textlength(prize, font=font_prize)
        draw.text(((width-pw)/2, 150),
                  prize,
                  font=font_prize,
                  fill=(230,230,255))

        # ===== GLOWING AS LOGO =====
        as_x = width - 130
        as_y = 20

        for blur in [20,10,5]:
            glow = Image.new("RGBA", img.size, (0,0,0,0))
            g_draw = ImageDraw.Draw(glow)
            g_draw.text((as_x, as_y), "AS",
                        font=font_logo,
                        fill=(255,255,255,200))
            glow = glow.filter(ImageFilter.GaussianBlur(blur))
            img = Image.alpha_composite(img, glow)

        draw = ImageDraw.Draw(img)
        draw.text((as_x, as_y),
                  "AS",
                  font=font_logo,
                  fill=(255,255,255))

        # ===== ANIMATED BOTTOM STRIPE =====
        stripe_layer = Image.new("RGBA", (width * 2, height), (0,0,0,0))
        s_draw = ImageDraw.Draw(stripe_layer)

        stripe_y = height - 50
        stripe_spacing = 150
        stripe_width = 70

        for i in range(0, width * 2, stripe_spacing):
            s_draw.polygon([
                (i, stripe_y),
                (i + stripe_width, stripe_y),
                (i + stripe_width - 20, stripe_y + 40),
                (i - 20, stripe_y + 40)
            ], fill=(255,255,255,200))

        stripe_offset = (frame * 6) % stripe_spacing
        stripe_crop = stripe_layer.crop(
            (stripe_spacing - stripe_offset, 0,
             stripe_spacing - stripe_offset + width, height)
        )

        img = Image.alpha_composite(img, stripe_crop)

        frames.append(img.convert("RGB"))

    path = f"giveaway_{random.randint(1,999999)}.gif"
    frames[0].save(
        path,
        save_all=True,
        append_images=frames[1:],
        duration=60,
        loop=0
    )

    return path

@bot.event
async def on_member_join(member):
    channel = bot.get_channel(WELCOME_CHANNEL_ID)
    gif = await create_welcome_gif(member)
    await channel.send(
        content=f"{member.mention}, Welcome!",
        file=discord.File(gif)
    )

# ================= GIVEAWAY GIF =================

async def create_giveaway_gif(prize):
    width, height = 800, 300
    frames = []

    font_big = ImageFont.truetype("Montserrat-Bold.ttf", 70)
    font_small = ImageFont.truetype("Montserrat-Regular.ttf", 40)

    bg = generate_background(width, height)
    sequence = ["G","GI","GIV","GIVE","GIVEA","GIVEAW","GIVEAWA","GIVEAWAY"]

    for i in range(len(sequence)*5):
        img = bg.copy()
        draw = ImageDraw.Draw(img)
        text = sequence[min(len(sequence)-1, i//5)]
        draw.text((200,60), text, font=font_big, fill=(255,255,255))
        draw.text((200,160), prize, font=font_small, fill=(230,230,255))
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
        required_role, ended = c.fetchone()

        if ended:
            await interaction.response.send_message("Ended.", ephemeral=True)
            return

        if required_role and required_role not in [r.id for r in interaction.user.roles]:
            await interaction.response.send_message("Missing required role.", ephemeral=True)
            return

        c.execute("SELECT 1 FROM entries WHERE giveaway_id=? AND user_id=?", (self.gid, interaction.user.id))
        if c.fetchone():
            await interaction.response.send_message("Already entered.", ephemeral=True)
            return

        entries = 1
        if BOOSTER_ROLE_ID in [r.id for r in interaction.user.roles]:
            entries += 5
        if VIP_ROLE_ID in [r.id for r in interaction.user.roles]:
            entries += 2

        for _ in range(entries):
            c.execute("INSERT INTO entries VALUES (?,?)", (self.gid, interaction.user.id))
        conn.commit()

        c.execute("SELECT COUNT(*) FROM entries WHERE giveaway_id=?", (self.gid,))
        total = c.fetchone()[0]

        embed = interaction.message.embeds[0]
        embed.set_field_at(4, name="🎟 Entries", value=str(total), inline=True)
        await interaction.message.edit(embed=embed)

        await interaction.response.send_message(f"Entered with {entries} entries!", ephemeral=True)

# ================= GIVEAWAY COMMAND =================

@bot.tree.command(name="giveaway")
async def giveaway(interaction: discord.Interaction,
                   duration: str,
                   winners: int,
                   prize: str,
                   required_role: discord.Role = None):

    seconds = parse_duration(duration)
    if not seconds:
        await interaction.response.send_message("Invalid duration.", ephemeral=True)
        return

    await interaction.response.defer()

    end_time = int(datetime.datetime.utcnow().timestamp()) + seconds
    gid = str(interaction.id)

    gif_path = await create_giveaway_gif(prize)
    file = discord.File(gif_path)

    embed = discord.Embed(title="🎉 GIVEAWAY 🎉")
    embed.set_image(url=f"attachment://{os.path.basename(gif_path)}")
    embed.add_field(name="🎁 Prize", value=prize)
    embed.add_field(name="👥 Winners", value=str(winners))
    embed.add_field(name="⏳ Ends", value=f"<t:{end_time}:R>")
    embed.add_field(name="🎟 Entries", value="0")

    view = GiveawayView(gid)

    await interaction.followup.send(embed=embed, view=view, file=file)
    msg = await interaction.original_response()

    c.execute("""
    INSERT INTO giveaways VALUES (?,?,?,?,?,?,?,?)
    """, (
        gid,
        msg.id,
        interaction.channel.id,
        end_time,
        winners,
        prize,
        required_role.id if required_role else None,
        0
    ))
    conn.commit()

    bot.loop.create_task(countdown(gid))

# ================= COUNTDOWN =================

async def countdown(gid):
    while True:
        c.execute("SELECT end_time, ended FROM giveaways WHERE id=?", (gid,))
        end_time, ended = c.fetchone()
        if ended:
            return
        if end_time - int(datetime.datetime.utcnow().timestamp()) <= 0:
            await end_giveaway(gid)
            return
        await asyncio.sleep(5)

async def end_giveaway(gid):
    c.execute("SELECT channel_id, message_id, winners, prize FROM giveaways WHERE id=?", (gid,))
    channel_id, message_id, winner_count, prize = c.fetchone()

    c.execute("UPDATE giveaways SET ended=1 WHERE id=?", (gid,))
    conn.commit()

    c.execute("SELECT user_id FROM entries WHERE giveaway_id=?", (gid,))
    entries = [r[0] for r in c.fetchall()]

    winners = random.sample(entries, min(winner_count, len(entries))) if entries else []

    channel = bot.get_channel(channel_id)
    message = await channel.fetch_message(message_id)

    mentions = " ".join(f"<@{w}>" for w in winners) if winners else "None"

    embed = discord.Embed(
        title="🎉 GIVEAWAY ENDED 🎉",
        description="🎊 Congratulations! 🎊",
        color=discord.Color.gold()
    )

    embed.add_field(name="🎁 Prize", value=prize, inline=False)
    embed.add_field(name="🏆 Winners", value=mentions, inline=False)

    await message.edit(embed=embed, view=None)

    # CONFETTI MESSAGE
    await channel.send("🎉 🎊 🎉 🎊 🎉 🎊 🎉 🎊 🎉")

bot.run(TOKEN)

