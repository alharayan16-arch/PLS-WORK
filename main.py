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


async def create_welcome_image(member):
    width, height = 1000, 400

    font_title = ImageFont.truetype("Montserrat-Bold.ttf", 70)
    font_user = ImageFont.truetype("Montserrat-Regular.ttf", 40)
    font_small = ImageFont.truetype("Montserrat-Regular.ttf", 26)
    font_logo = ImageFont.truetype("Montserrat-Bold.ttf", 35)

    username = member.display_name
    member_number = member.guild.member_count
    join_time = datetime.datetime.utcnow().strftime("%H:%M UTC")

    # --------- BACKGROUND ----------
    bg = Image.new("RGB", (width, height), (20, 0, 35))
    draw = ImageDraw.Draw(bg)

    # Smooth vertical gradient
    top_color = (90, 0, 160)
    bottom_color = (10, 0, 20)

    for y in range(height):
        ratio = y / height
        r = int(top_color[0] * (1 - ratio) + bottom_color[0] * ratio)
        g = int(top_color[1] * (1 - ratio) + bottom_color[1] * ratio)
        b = int(top_color[2] * (1 - ratio) + bottom_color[2] * ratio)
        draw.line([(0, y), (width, y)], fill=(r, g, b))

    img = bg.convert("RGBA")
    draw = ImageDraw.Draw(img)

    # --------- DIAGONAL RIGHT SHAPE ----------
    diagonal = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    d_draw = ImageDraw.Draw(diagonal)

    d_draw.polygon([
        (width * 0.65, 0),
        (width, 0),
        (width, height),
        (width * 0.85, height)
    ], fill=(0, 0, 0, 80))

    img = Image.alpha_composite(img, diagonal)
    draw = ImageDraw.Draw(img)

    # --------- DOWNLOAD AVATAR ----------
    async with aiohttp.ClientSession() as session:
        async with session.get(member.display_avatar.url) as resp:
            avatar_bytes = await resp.read()

    avatar = Image.open(io.BytesIO(avatar_bytes)).convert("RGBA")
    avatar = avatar.resize((110, 110))

    mask = Image.new("L", (110, 110), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, 110, 110), fill=255)
    avatar.putalpha(mask)

    img.paste(avatar, (60, 170), avatar)

    # --------- TEXT ----------
    draw.text((60, 70),
              "Welcome",
              font=font_title,
              fill=(255, 255, 255))

    # Accent line under Welcome
    draw.rectangle(
        (60, 140, 260, 150),
        fill=(140, 80, 255)
    )

    draw.text((200, 170),
              username,
              font=font_user,
              fill=(255, 255, 255))

    # --------- MEMBER BADGE ----------
    badge_x = 200
    badge_y = 220
    badge_width = 150
    badge_height = 40

    draw.rounded_rectangle(
        (badge_x, badge_y,
         badge_x + badge_width,
         badge_y + badge_height),
        radius=20,
        fill=(140, 80, 255, 200)
    )

    draw.text((badge_x + 25, badge_y + 6),
              f"#{member_number}",
              font=font_small,
              fill=(255, 255, 255))

    # Time under badge
    draw.text((200, 270),
              join_time,
              font=font_small,
              fill=(210, 210, 255))

    # --------- AS LOGO BOTTOM LEFT ----------
    draw.text((60, height - 60),
              "AS",
              font=font_logo,
              fill=(255, 255, 255))

    return img.convert("RGB")


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
            file=discord.File(fp=image_binary, filename="welcome.png")
        )


bot.run(TOKEN)
