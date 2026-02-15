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

    try:
        font_big = ImageFont.truetype("Montserrat-Bold.ttf", 60)
        font_small = ImageFont.truetype("Montserrat-Regular.ttf", 28)
        font_logo = ImageFont.truetype("Montserrat-Bold.ttf", 160)

    except:
        font_big = ImageFont.load_default()
        font_small = ImageFont.load_default()
        font_logo = ImageFont.load_default()

    username = member.name
    member_count = f"Member #{member.guild.member_count}"
    join_time = datetime.datetime.utcnow().strftime("%H:%M UTC")

    async with aiohttp.ClientSession() as session:
        async with session.get(member.display_avatar.url) as resp:
            avatar_bytes = await resp.read()

    avatar = Image.open(io.BytesIO(avatar_bytes)).convert("RGBA")
    avatar = avatar.resize((55, 55))

    mask = Image.new("L", (55, 55), 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.ellipse((0, 0, 55, 55), fill=255)
    avatar.putalpha(mask)

    total_frames = 40

    for i in range(total_frames):
        img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        draw.text((50, 60), f"Welcome {username}", font=font_big, fill=(255, 255, 255, 255))

        img.paste(avatar, (50, 135), avatar)

        draw.text((120, 140), member_count, font=font_small, fill=(180, 180, 255, 255))
        draw.text((120, 170), join_time, font=font_small, fill=(180, 180, 255, 255))

        movement_range = 2
        offset_x = int(math.sin(i / 16) * movement_range)

        logo_x = width - 260 + offset_x
        logo_y = 20

        pulse = (math.sin(i / 10) + 1) / 2
        glow_alpha = int(170 + pulse * 60)

        glow_layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        glow_draw = ImageDraw.Draw(glow_layer)

        glow_draw.text((logo_x, logo_y), "AS", font=font_logo, fill=(255, 255, 255, glow_alpha))
        glow_layer = glow_layer.filter(ImageFilter.GaussianBlur(6))

        img = Image.alpha_composite(img, glow_layer)

        draw = ImageDraw.Draw(img)
        draw.text((logo_x, logo_y), "AS", font=font_logo, fill=(255, 255, 255, 255))

        frames.append(img)

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

