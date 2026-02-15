import discord
from discord.ext import commands
from PIL import Image, ImageDraw, ImageFont
import datetime
import aiohttp
import io
import os

TOKEN = os.getenv("TOKEN")
WELCOME_CHANNEL_ID = 1472224372382109905

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")


async def create_welcome_gif(member):
    width, height = 900, 350
    frames = []

    # Fonts (Noto for multilingual support)
    font_title = ImageFont.truetype("NotoSans-Bold.ttf", 65)
    font_user = ImageFont.truetype("NotoSans-Regular.ttf", 38)
    font_small = ImageFont.truetype("NotoSans-Regular.ttf", 26)
    font_logo = ImageFont.truetype("Montserrat-Bold.ttf", 32)

    username = member.display_name
    member_count = f"Member #{member.guild.member_count}"
    join_time = datetime.datetime.now(datetime.UTC).strftime("%H:%M UTC")

    languages = [
        "Welcome",
        "مرحبا",        # Arabic
        "स्वागत है",     # Hindi
        "Willkommen",   # German
        "欢迎",          # Chinese
        "Benvenuto"     # Italian
    ]

    # -------- CLEAN PURPLE BACKGROUND --------
    base_bg = Image.new("RGBA", (width, height), (88, 0, 170, 255))
    bg_draw = ImageDraw.Draw(base_bg)

    # smooth vertical fade (NO LINES)
    for y in range(height):
        ratio = y / height
        r = int(88 * (1 - ratio))
        g = 0
        b = int(170 * (1 - ratio))
        bg_draw.line([(0, y), (width, y)], fill=(r, g, b, 255))

    # -------- DOWNLOAD AVATAR --------
    async with aiohttp.ClientSession() as session:
        async with session.get(member.display_avatar.url) as resp:
            avatar_bytes = await resp.read()

    avatar = Image.open(io.BytesIO(avatar_bytes)).convert("RGBA")
    avatar = avatar.resize((100, 100))

    mask = Image.new("L", (100, 100), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, 100, 100), fill=255)
    avatar.putalpha(mask)

    spacing = 60
    total_frames = 120  # safe size

    for frame in range(total_frames):

        img = base_bg.copy()
        draw = ImageDraw.Draw(img)

        # -------- XO PATTERN (INFINITE SMOOTH) --------
        pattern = Image.new("RGBA", (width + spacing, height), (0, 0, 0, 0))
        p_draw = ImageDraw.Draw(pattern)

        offset = (frame * 5) % spacing  # faster smooth

        for y in range(0, height, spacing):
            for x in range(0, width + spacing, spacing):
                p_draw.text((x, y), "X",
                            font=font_logo,
                            fill=(255, 255, 255, 18))
                p_draw.text((x + 25, y + 25), "O",
                            font=font_logo,
                            fill=(255, 255, 255, 18))

        cropped = pattern.crop((offset, 0, offset + width, height))
        img = Image.alpha_composite(img, cropped)

        draw = ImageDraw.Draw(img)

        # -------- LANGUAGE SLIDE (CONTINUOUS) --------
        lang_index = (frame // 20) % len(languages)
        next_lang = (lang_index + 1) % len(languages)

        progress = (frame % 20) / 20
        y_offset = int(progress * 80)

        draw.text((60, 60 - y_offset),
                  languages[lang_index],
                  font=font_title,
                  fill=(255, 255, 255))

        draw.text((60, 140 - y_offset),
                  languages[next_lang],
                  font=font_title,
                  fill=(255, 255, 255))

        # -------- AVATAR --------
        img.paste(avatar, (60, 150), avatar)

        # -------- USER INFO --------
        draw.text((180, 150),
                  username,
                  font=font_user,
                  fill=(255, 255, 255))

        draw.text((180, 195),
                  member_count,
                  font=font_small,
                  fill=(220, 220, 255))

        draw.text((180, 225),
                  join_time,
                  font=font_small,
                  fill=(220, 220, 255))

        # -------- AS LOGO --------
        draw.text((60, height - 55),
                  "AS",
                  font=font_logo,
                  fill=(255, 255, 255))

        # reduce palette (IMPORTANT)
        img = img.convert("P", palette=Image.ADAPTIVE, colors=128)

        frames.append(img)

    gif_path = f"welcome_{member.id}.gif"

    frames[0].save(
        gif_path,
        save_all=True,
        append_images=frames[1:],
        duration=40,
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


@bot.command()
async def testwelcome(ctx):
    member = ctx.author

    gif = await create_welcome_gif(member)

    await ctx.send(
        file=discord.File(gif)
    )


bot.run(TOKEN)
