import discord
from discord.ext import commands
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import datetime
import math
import aiohttp
import io
import os

TOKEN = os.getenv("TOKEN")  # ✅ FIXED
WELCOME_CHANNEL_ID = 1472224372382109905

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")


# ---------------- GIF CREATION ----------------
async def create_welcome_gif(member):
    width, height = 900, 300
    frames = []

    # Load fonts (no fallback needed now)
    font_big = ImageFont.truetype("Montserrat-Bold.ttf", 60)
    font_small = ImageFont.truetype("Montserrat-Regular.ttf", 28)
    font_logo = ImageFont.truetype("Montserrat-Bold.ttf", 160)

    # ✅ USE DISPLAY NAME
    username = member.display_name

    member_count = f"Member #{member.guild.member_count}"
    join_time = datetime.datetime.utcnow().strftime("%H:%M UTC")

    # Download avatar
    async with aiohttp.ClientSession() as session:
        async with session.get(member.display_avatar.url) as resp:
            avatar_bytes = await resp.read()

    avatar = Image.open(io.BytesIO(avatar_bytes)).convert("RGBA")
    avatar = avatar.resize((80, 80))

    mask = Image.new("L", (80, 80), 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.ellipse((0, 0, 80, 80), fill=255)
    avatar.putalpha(mask)

    total_frames = 40

    for i in range(total_frames):

        # --------- VIOLET → BLACK GRADIENT BACKGROUND ----------
      # --------- SMOOTH VIOLET → BLACK GRADIENT ----------
bg = Image.new("RGB", (width, height))
pixels = bg.load()

top_color = (75, 0, 130)     # deep violet
bottom_color = (0, 0, 0)     # black

for y in range(height):
    ratio = y / (height - 1)
    r = int(top_color[0] * (1 - ratio) + bottom_color[0] * ratio)
    g = int(top_color[1] * (1 - ratio) + bottom_color[1] * ratio)
    b = int(top_color[2] * (1 - ratio) + bottom_color[2] * ratio)

    for x in range(width):
        pixels[x, y] = (r, g, b)

img = bg.convert("RGBA")
draw = ImageDraw.Draw(img)


        # Welcome text
        draw.text((50, 70), f"Welcome {username}", font=font_big, fill=(255, 255, 255))

        # Avatar
        img.paste(avatar, (50, 150), avatar)

        # Member info
        draw.text((150, 160), member_count, font=font_small, fill=(200, 200, 255))
        draw.text((150, 190), join_time, font=font_small, fill=(200, 200, 255))

        # --------- AS GLOW ----------
        pulse = (math.sin(i / 8) + 1) / 2
        glow_alpha = int(160 + pulse * 80)

        glow_layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        glow_draw = ImageDraw.Draw(glow_layer)

        glow_draw.text((width - 260, 30), "AS",
                       font=font_logo,
                       fill=(255, 255, 255, glow_alpha))

        glow_layer = glow_layer.filter(ImageFilter.GaussianBlur(8))
        img = Image.alpha_composite(img, glow_layer)

        draw = ImageDraw.Draw(img)
        draw.text((width - 260, 30), "AS",
                  font=font_logo,
                  fill=(255, 255, 255))

        frames.append(img)

    # Save GIF
    gif_path = f"welcome_{member.id}.gif"

    frames[0].save(
        gif_path,
        save_all=True,
        append_images=frames[1:],
        duration=60,
        loop=0,
        disposal=2
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
        content=f"{member.mention}, Welcome to Arab’s Studio — we’re glad to have you here!",
        file=discord.File(gif)
    )


bot.run(TOKEN)

