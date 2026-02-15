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
    font_small = ImageFont.truetype("Montserrat-Regular.ttf", 28)
    font_logo = ImageFont.truetype("Montserrat-Bold.ttf", 35)

    username = member.display_name
    member_count = f"Member #{member.guild.member_count}"
    join_time = datetime.datetime.utcnow().strftime("%H:%M UTC")

    # --------- BASE DARK BACKGROUND ----------
    bg = Image.new("RGB", (width, height), (15, 0, 30))
    draw = ImageDraw.Draw(bg)

    # --------- VIOLET GRADIENT OVERLAY ----------
    for y in range(height):
        ratio = y / height
        r = int(80 * (1 - ratio))
        g = 0
        b = int(150 * (1 - ratio))
        draw.line([(0, y), (width, y)], fill=(r, g, b))

    # --------- PATTERN OVERLAY ----------
    pattern_color = (255, 255, 255, 15)
    pattern = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    p_draw = ImageDraw.Draw(pattern)

    spacing = 60
    for y in range(0, height, spacing):
        for x in range(0, width, spacing):
            p_draw.text((x, y), "X", font=font_logo, fill=pattern_color)
            p_draw.text((x + 25, y + 25), "O", font=font_logo, fill=pattern_color)

    bg = Image.alpha_composite(bg.convert("RGBA"), pattern)

    draw = ImageDraw.Draw(bg)

    # --------- DOWNLOAD AVATAR ----------
    async with aiohttp.ClientSession() as session:
        async with session.get(member.display_avatar.url) as resp:
            avatar_bytes = await resp.read()

    avatar = Image.open(io.BytesIO(avatar_bytes)).convert("RGBA")
    avatar = avatar.resize((110, 110))

    mask = Image.new("L", (110, 110), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, 110, 110), fill=255)
    avatar.putalpha(mask)

    bg.paste(avatar, (60, 150), avatar)

    # --------- TEXT ----------
    draw.text((60, 60), "Welcome", font=font_title, fill=(255, 255, 255))
    draw.text((200, 150), username, font=font_user, fill=(255, 255, 255))
    draw.text((200, 200), member_count, font=font_small, fill=(200, 200, 255))
    draw.text((200, 230), join_time, font=font_small, fill=(200, 200, 255))

    # --------- BOTTOM LEFT AS LOGO ----------
    draw.text((60, height - 60),
              "AS",
              font=font_logo,
              fill=(255, 255, 255))

    return bg.convert("RGB")


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
