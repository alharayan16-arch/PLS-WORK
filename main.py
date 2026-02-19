import discord
from discord.ext import commands
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import datetime
import aiohttp
import io
import os
import random
import json
import asyncio

TOKEN = os.getenv("TOKEN")

WELCOME_CHANNEL_ID = 1472224372382109905
SUPPORT_CHANNEL_ID = 1472228682566340842
STAFF_LOG_CHANNEL_ID = 1473910880264519730
GIVEAWAY_FILE = "giveaways.json"

GW_COLOR = discord.Color(0x5E17EB)

intents = discord.Intents.all()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ================= STORAGE =================

def load_giveaways():
    if not os.path.exists(GIVEAWAY_FILE):
        return {}
    with open(GIVEAWAY_FILE, "r") as f:
        return json.load(f)

def save_giveaways(data):
    with open(GIVEAWAY_FILE, "w") as f:
        json.dump(data, f, indent=4)

# ================= TIME FORMAT =================

def format_duration(seconds):
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60

    parts = []

    if hours > 0:
        parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
    if minutes > 0:
        parts.append(f"{minutes} min")
    if secs > 0:
        parts.append(f"{secs} sec")

    if not parts:
        return "0 sec"

    return " ".join(parts)

# ================= READY =================

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Logged in as {bot.user}")

# ================= YOUR ORIGINAL WELCOME SYSTEM =================
# (UNCHANGED — EXACTLY AS YOU PROVIDED)

async def create_welcome_gif(member):
    width, height = 1000, 400
    frames = []

    font_title = ImageFont.truetype("Montserrat-Bold.ttf", 70)
    font_user = ImageFont.truetype("Montserrat-Regular.ttf", 40)
    font_small = ImageFont.truetype("Montserrat-Regular.ttf", 28)
    font_logo = ImageFont.truetype("Montserrat-Bold.ttf", 110)
    font_link = ImageFont.truetype("Montserrat-Regular.ttf", 24)

    sequences = [
        ["W","WE","WEL","WELC","WELCO","WELCOM","WELCOME"],
        ["W","WI","WIL","WILL","WILLK","WILLKO","WILLKOM","WILLKOMM","WILLKOMME","WILLKOMMEN"],
        ["B","BE","BEN","BENV","BENVE","BENVEN","BENVENU","BENVENUT","BENVENUTO"],
    ]

    username = member.display_name
    member_count = f"Member #{member.guild.member_count}"
    join_time = datetime.datetime.now(datetime.timezone.utc).strftime("%H:%M UTC")

    # DARK DIAGONAL BACKGROUND
    base_bg = Image.new("RGB", (width, height))
    bg_draw = ImageDraw.Draw(base_bg)

    for y in range(height):
        for x in range(width):
            ratio = (x + y) / (width + height)
            r = int(55 - ratio * 30)
            g = 0
            b = int(105 - ratio * 50)
            bg_draw.point((x, y), fill=(r, g, b))

    base_bg = base_bg.convert("RGBA")

    # AVATAR
    async with aiohttp.ClientSession() as session:
        async with session.get(member.display_avatar.url) as resp:
            avatar_bytes = await resp.read()

    avatar = Image.open(io.BytesIO(avatar_bytes)).convert("RGBA")
    avatar = avatar.resize((110, 110))

    mask = Image.new("L", (110, 110), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, 110, 110), fill=255)
    avatar.putalpha(mask)

    spacing = 60
    typing_speed = 6
    cycle_lengths = [len(seq) * typing_speed for seq in sequences]
    total_cycle = sum(cycle_lengths)
    total_frames = total_cycle + 30

    for frame in range(total_frames):
        img = base_bg.copy()
        draw = ImageDraw.Draw(img)

        # XO PATTERN
        pattern_layer = Image.new("RGBA", (width * 2, height), (0, 0, 0, 0))
        p_draw = ImageDraw.Draw(pattern_layer)

        for y in range(0, height, spacing):
            for x in range(0, width * 2, spacing):
                p_draw.text((x, y), "X", font=font_small, fill=(255, 255, 255, 50))
                p_draw.text((x + 25, y + 25), "O", font=font_small, fill=(255, 255, 255, 50))

        offset = (frame * 4) % spacing
        cropped_pattern = pattern_layer.crop((offset, 0, offset + width, height))
        img = Image.alpha_composite(img, cropped_pattern)
        draw = ImageDraw.Draw(img)

        # TYPING LOGIC
        cycle_frame = frame % total_cycle
        cumulative = 0

        for seq, seq_length in zip(sequences, cycle_lengths):
            if cycle_frame < cumulative + seq_length:
                local_frame = cycle_frame - cumulative
                letter_index = min(len(seq)-1, local_frame // typing_speed)
                welcome_text = seq[letter_index]
                break
            cumulative += seq_length

        draw.text((60, 60), welcome_text, font=font_title, fill=(255, 255, 255))

        # USER INFO
        draw.text((200, 150), username, font=font_user, fill=(255, 255, 255))
        draw.text((200, 200), member_count, font=font_small, fill=(230, 230, 255))
        draw.text((200, 230), join_time, font=font_small, fill=(230, 230, 255))

        img.paste(avatar, (60, 150), avatar)

        # MOVING STRIPES (BOTTOM)
        stripe_canvas = Image.new("RGBA", (width * 2, height), (0, 0, 0, 0))
        s_draw = ImageDraw.Draw(stripe_canvas)

        stripe_y = height - 80
        stripe_height = 60
        stripe_spacing = 180
        stripe_width = 90

        for i in range(0, width * 2, stripe_spacing):
            x = i
            s_draw.polygon([
                (x, stripe_y),
                (x + stripe_width, stripe_y),
                (x + stripe_width - 35, stripe_y + stripe_height),
                (x - 35, stripe_y + stripe_height)
            ], fill=(255, 255, 255, 245))

        stripe_offset = (frame * 6) % stripe_spacing
        cropped_stripes = stripe_canvas.crop(
            (stripe_spacing - stripe_offset, 0, stripe_spacing - stripe_offset + width, height)
        )

        img = Image.alpha_composite(img, cropped_stripes)
        draw = ImageDraw.Draw(img)

        # AS LOGO TOP RIGHT
        letter_spacing = -8
        a_width = draw.textlength("A", font=font_logo)
        s_width = draw.textlength("S", font=font_logo)

        as_total_width = a_width + s_width + letter_spacing
        as_x = width - as_total_width - 140
        as_y = 40

        # Glow effect
        for glow in [45, 30, 15]:
            glow_layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
            glow_draw = ImageDraw.Draw(glow_layer)

            glow_draw.text((as_x, as_y - 12), "A", font=font_logo, fill=(255, 255, 255, 220))
            glow_draw.text((as_x + a_width + letter_spacing, as_y), "S", font=font_logo, fill=(255, 255, 255, 220))

            glow_layer = glow_layer.filter(ImageFilter.GaussianBlur(glow))
            img = Image.alpha_composite(img, glow_layer)

        draw = ImageDraw.Draw(img)
        draw.text((as_x, as_y - 12), "A", font=font_logo, fill=(255, 255, 255))
        draw.text((as_x + a_width + letter_spacing, as_y), "S", font=font_logo, fill=(255, 255, 255))

        # SERVER LINK
        draw.text((as_x - 100, as_y + 115), "https://discord.gg/arabsstudio", font=font_link, fill=(255, 255, 255, 160))

        frames.append(img)

    gif_path = f"welcome_{member.id}.gif"
    frames[0].save(
        gif_path,
        save_all=True,
        append_images=frames[1:],
        duration=60,
        loop=0,
        disposal=2,
        optimize=True
    )

    return gif_path

@bot.event
async def on_member_join(member):
    channel = bot.get_channel(WELCOME_CHANNEL_ID)
    gif = await create_welcome_gif(member)
    await channel.send(
        content=f"{member.mention}, Welcome to Arab’s Studio — we’re glad to have you here!",
        file=discord.File(gif)
    )

# ================= GIVEAWAY WITH LIVE COUNTDOWN =================

@bot.tree.command(name="giveaway", description="Start a giveaway with live countdown")
async def giveaway(interaction: discord.Interaction, duration_seconds: int, winners: int, prize: str, requirements: str = "None"):

    if not interaction.user.guild_permissions.manage_guild:
        await interaction.response.send_message("Need Manage Server permission.", ephemeral=True)
        return

    end_time = datetime.datetime.utcnow() + datetime.timedelta(seconds=duration_seconds)

    embed = discord.Embed(title="✨ ARAB'S STUDIO GIVEAWAY ✨", color=GW_COLOR)
    embed.add_field(name="🎁 Prize", value=prize, inline=False)
    embed.add_field(name="👥 Winners", value=str(winners), inline=False)
    embed.add_field(name="📌 Requirements", value=requirements, inline=False)
    embed.add_field(name="⏳ Ends In", value=format_duration(duration_seconds), inline=False)

    await interaction.response.send_message(embed=embed)
    message = await interaction.original_response()

    remaining = duration_seconds

    while remaining > 0:
        await asyncio.sleep(1)
        remaining -= 1

        embed.set_field_at(3, name="⏳ Ends In", value=format_duration(remaining), inline=False)
        await message.edit(embed=embed)

    embed.title = "🎉 GIVEAWAY ENDED"
    embed.set_field_at(3, name="⏳ Ended", value="Giveaway finished", inline=False)
    await message.edit(embed=embed)

bot.run(TOKEN)

