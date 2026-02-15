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
    frames = []

    font_title = ImageFont.truetype("Montserrat-Bold.ttf", 70)
    font_user = ImageFont.truetype("Montserrat-Regular.ttf", 40)
    font_small = ImageFont.truetype("Montserrat-Regular.ttf", 28)
    font_logo = ImageFont.truetype("Montserrat-Bold.ttf", 35)

    username = member.display_name
    member_count = f"Member #{member.guild.member_count}"
    join_time = datetime.datetime.utcnow().strftime("%H:%M UTC")

    # --------- BASE BACKGROUND ----------
    base_bg = Image.new("RGB", (width, height), (15, 0, 30))
    draw_base = ImageDraw.Draw(base_bg)

    for y in range(height):
        ratio = y / height
        r = int(80 * (1 - ratio))
        g = 0
        b = int(150 * (1 - ratio))
        draw_base.line([(0, y), (width, y)], fill=(r, g, b))

    total_frames = 40
    spacing = 60

    # Download avatar ONCE (not every frame)
    async with aiohttp.ClientSession() as session:
        async with session.get(member.display_avatar.url) as resp:
            avatar_bytes = await resp.read()

    avatar = Image.open(io.BytesIO(avatar_bytes)).convert("RGBA")
    avatar = avatar.resize((110, 110))

    mask = Image.new("L", (110, 110), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, 110, 110), fill=255)
    avatar.putalpha(mask)

    for frame in range(total_frames):
        img = base_bg.copy().convert("RGBA")
        draw = ImageDraw.Draw(img)

        # --------- MOVING X O PATTERN ----------
        pattern_layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        p_draw = ImageDraw.Draw(pattern_layer)

        offset = (frame * 4) % spacing  # speed control

        for y in range(0, height, spacing):
            for x in range(-spacing, width, spacing):
                p_draw.text((x + offset, y),
                            "X",
                            font=font_logo,
                            fill=(255, 255, 255, 20))
                p_draw.text((x + 25 + offset, y + 25),
                            "O",
                            font=font_logo,
                            fill=(255, 255, 255, 20))

        img = Image.alpha_composite(img, pattern_layer)
        draw = ImageDraw.Draw(img)

        # --------- AVATAR ----------
        img.paste(avatar, (60, 150), avatar)

        # --------- TEXT ----------
        draw.text((60, 60), "Welcome", font=font_title, fill=(255, 255, 255))
        draw.text((200, 150), username, font=font_user, fill=(255, 255, 255))
        draw.text((200, 200), member_count, font=font_small, fill=(200, 200, 255))
        draw.text((200, 230), join_time, font=font_small, fill=(200, 200, 255))

        # --------- AS LOGO ----------
        draw.text((60, height - 60),
                  "AS",
                  font=font_logo,
                  fill=(255, 255, 255))

        frames.append(img)

    gif_path = f"welcome_{member.id}.gif"

    frames[0].save(
        gif_path,
        save_all=True,
        append_images=frames[1:],
        duration=80,
        loop=0,
        disposal=2,
        optimize=True
    )

    return gif_path


@bot.event
async def on_member_join(member):
    channel = bot.get_channel(WELCOME_CHANNEL_ID)

    gif = await create_welcome_image(member)

    await channel.send(
        content=f"{member.mention}, Welcome to Arab’s Studio — we’re glad to have you here!",
        file=discord.File(gif)
    )


@bot.command()
async def testwelcome(ctx):
    member = ctx.author

    gif = await create_welcome_image(member)

    await ctx.send(
        content=f"{member.mention}, Welcome to Arab’s Studio — we’re glad to have you here!",
        file=discord.File(gif)
    )


bot.run(TOKEN)
