import discord
from discord.ext import commands
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import datetime
import aiohttp
import io
import os
import arabic_reshaper
from bidi.algorithm import get_display

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

    font_title = ImageFont.truetype("NotoSans-Bold.ttf", 70)
    font_user = ImageFont.truetype("NotoSans-Regular.ttf", 40)
    font_small = ImageFont.truetype("NotoSans-Regular.ttf", 28)
    font_logo = ImageFont.truetype("NotoSans-Bold.ttf", 35)

    username = member.display_name
    member_count = f"Member #{member.guild.member_count}"
    join_time = datetime.datetime.now(datetime.timezone.utc).strftime("%H:%M UTC")

    arabic_text = get_display(arabic_reshaper.reshape("مرحبًا"))

    welcome_texts = [
        "Welcome",
        arabic_text,
        "स्वागत है",
        "Willkommen",
        "欢迎",
        "Benvenuto"
    ]

    # ---------- BACKGROUND ----------
    base_bg = Image.new("RGBA", (width, height))
    pixels = base_bg.load()

    base_color = (110, 0, 200)
    dark_color = (30, 0, 60)

    for y in range(height):
        for x in range(width):
            ratio = (x + y) / (width + height)
            r = int(base_color[0] * (1 - ratio) + dark_color[0] * ratio)
            g = int(base_color[1] * (1 - ratio) + dark_color[1] * ratio)
            b = int(base_color[2] * (1 - ratio) + dark_color[2] * ratio)
            pixels[x, y] = (r, g, b, 255)

    base_bg = base_bg.filter(ImageFilter.GaussianBlur(1))

    # ---------- AVATAR ----------
    async with aiohttp.ClientSession() as session:
        async with session.get(member.display_avatar.url) as resp:
            avatar_bytes = await resp.read()

    avatar = Image.open(io.BytesIO(avatar_bytes)).convert("RGBA")
    avatar = avatar.resize((110, 110))

    mask = Image.new("L", (110, 110), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, 110, 110), fill=255)
    avatar.putalpha(mask)

    # ---------- ANIMATION SETTINGS ----------
    spacing = 60
    pattern_speed = 4
    slide_speed = 3  # language scroll speed
    total_frames = 240  # smooth loop length

    global_frame = 0

    # Duplicate list for seamless infinite scroll
    scroll_texts = welcome_texts + welcome_texts

    for frame in range(total_frames):

        img = base_bg.copy()
        draw = ImageDraw.Draw(img)

        # ---------- CONTINUOUS PATTERN ----------
        pattern_layer = Image.new("RGBA", (width + spacing, height), (0, 0, 0, 0))
        p_draw = ImageDraw.Draw(pattern_layer)

        offset = global_frame * pattern_speed

        for y in range(0, height, spacing):
            for x in range(0, width + spacing, spacing):
                p_draw.text((x - offset % spacing, y),
                            "X",
                            font=font_logo,
                            fill=(255, 255, 255, 18))
                p_draw.text((x - offset % spacing + 25, y + 25),
                            "O",
                            font=font_logo,
                            fill=(255, 255, 255, 18))

        cropped_pattern = pattern_layer.crop((0, 0, width, height))
        img = Image.alpha_composite(img, cropped_pattern)

        draw = ImageDraw.Draw(img)

        # ---------- SLIDING LANGUAGE ----------
        scroll_position = frame * slide_speed

        for i, text in enumerate(scroll_texts):
            y_position = 60 + i * 90 - scroll_position

            if -100 < y_position < height:
                draw.text((60, y_position),
                          text,
                          font=font_title,
                          fill=(255, 255, 255))

        # ---------- AVATAR ----------
        img.paste(avatar, (60, 150), avatar)

        # ---------- USER INFO ----------
        draw.text((200, 150), username, font=font_user, fill=(255, 255, 255))
        draw.text((200, 200), member_count, font=font_small, fill=(220, 220, 255))
        draw.text((200, 230), join_time, font=font_small, fill=(220, 220, 255))

        # ---------- AS LOGO ----------
        draw.text((60, height - 60),
                  "AS",
                  font=font_logo,
                  fill=(255, 255, 255))

        frames.append(img)
        global_frame += 1

    gif_path = f"welcome_{member.id}.gif"

    frames[0].save(
        gif_path,
        save_all=True,
        append_images=frames[1:],
        duration=35,
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
    await ctx.send(file=discord.File(gif))


bot.run(TOKEN)
