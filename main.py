import discord
from discord.ext import commands
from PIL import Image, ImageDraw, ImageFont, ImageFilter
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


# ---------------- PREMIUM PNG CREATION ----------------
async def create_welcome_image(member):
    width, height = 1000, 350

    font_big = ImageFont.truetype("Montserrat-Bold.ttf", 65)
    font_small = ImageFont.truetype("Montserrat-Regular.ttf", 30)
    font_logo = ImageFont.truetype("Montserrat-Bold.ttf", 180)

    username = member.display_name
    member_count = f"Member #{member.guild.member_count}"
    join_time = datetime.datetime.utcnow().strftime("%H:%M UTC")

    # --------- SMOOTH GRADIENT BACKGROUND ----------
    bg = Image.new("RGB", (width, height))
    draw_bg = ImageDraw.Draw(bg)

    top_color = (100, 0, 170)   # violet
    bottom_color = (0, 0, 0)    # black

    for y in range(height):
        ratio = y / height
        r = int(top_color[0] * (1 - ratio) + bottom_color[0] * ratio)
        g = int(top_color[1] * (1 - ratio) + bottom_color[1] * ratio)
        b = int(top_color[2] * (1 - ratio) + bottom_color[2] * ratio)
        draw_bg.line([(0, y), (width, y)], fill=(r, g, b))

    bg = bg.filter(ImageFilter.GaussianBlur(2))
    img = bg.convert("RGBA")
    draw = ImageDraw.Draw(img)

    # --------- GLASS PANEL ----------
    panel_width = 820
    panel_height = 220
    panel_x = 90
    panel_y = 70

    panel = Image.new("RGBA", (panel_width, panel_height), (255, 255, 255, 30))
    panel = panel.filter(ImageFilter.GaussianBlur(8))

    img.paste(panel, (panel_x, panel_y), panel)

    # --------- DOWNLOAD AVATAR ----------
    async with aiohttp.ClientSession() as session:
        async with session.get(member.display_avatar.url) as resp:
            avatar_bytes = await resp.read()

    avatar = Image.open(io.BytesIO(avatar_bytes)).convert("RGBA")
    avatar = avatar.resize((110, 110))

    mask = Image.new("L", (110, 110), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, 110, 110), fill=255)
    avatar.putalpha(mask)

    img.paste(avatar, (panel_x + 40, panel_y + 55), avatar)

    # --------- TEXT ----------
    text_x = panel_x + 180

    draw.text((text_x, panel_y + 40),
              f"Welcome {username}",
              font=font_big,
              fill=(255, 255, 255))

    draw.text((text_x, panel_y + 120),
              member_count,
              font=font_small,
              fill=(220, 220, 255))

    draw.text((text_x, panel_y + 160),
              join_time,
              font=font_small,
              fill=(220, 220, 255))

    # --------- AS LOGO ----------
    logo_x = width - 300
    logo_y = 60

    glow_layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow_layer)

    glow_draw.text((logo_x, logo_y),
                   "AS",
                   font=font_logo,
                   fill=(255, 255, 255, 80))

    glow_layer = glow_layer.filter(ImageFilter.GaussianBlur(15))
    img = Image.alpha_composite(img, glow_layer)

    draw = ImageDraw.Draw(img)
    draw.text((logo_x, logo_y),
              "AS",
              font=font_logo,
              fill=(255, 255, 255))

    return img


# ---------------- EVENTS ----------------
@bot.event
async def on_member_join(member):
    channel = bot.get_channel(WELCOME_CHANNEL_ID)

    image = await create_welcome_image(member)

    with io.BytesIO() as image_binary:
        image.save(image_binary, format="PNG")
        image_binary.seek(0)

        await channel.send(
            content=f"{member.mention}, Welcome to Arab’s Studio — we’re glad to have you here!",
            file=discord.File(fp=image_binary, filename="welcome.png")
        )


@bot.command()
async def testwelcome(ctx):
    member = ctx.author

    image = await create_welcome_image(member)

    with io.BytesIO() as image_binary:
        image.save(image_binary, format="PNG")
        image_binary.seek(0)

        await ctx.send(
            content=f"{member.mention}, Welcome to Arab’s Studio — we’re glad to have you here!",
            file=discord.File(fp=image_binary, filename="welcome.png")
        )


bot.run(TOKEN)
