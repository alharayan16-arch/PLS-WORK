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

    welcome_texts = [
        "Welcome",
        "مرحبًا",
        "स्वागत है",
        "Willkommen",
        "欢迎",
        "Benvenuto"
    ]

    # --------- BACKGROUND ----------
    base_bg = Image.new("RGBA", (width, height), (20, 0, 40, 255))

    gradient_layer = Image.new("RGBA", (width, height))
    pixels = gradient_layer.load()

    base_color = (110, 0, 200)
    dark_color = (30, 0, 60)

    for y in range(height):
        for x in range(width):
            ratio = (x + y) / (width + height)
            r = int(base_color[0] * (1 - ratio) + dark_color[0] * ratio)
            g = int(base_color[1] * (1 - ratio) + dark_color[1] * ratio)
            b = int(base_color[2] * (1 - ratio) + dark_color[2] * ratio)
            pixels[x, y] = (r, g, b, 255)

    gradient_layer = gradient_layer.filter(ImageFilter.GaussianBlur(1))
    base_bg = Image.alpha_composite(base_bg, gradient_layer)

    # --------- AVATAR ----------
    async with aiohttp.ClientSession() as session:
        async with session.get(member.display_avatar.url) as resp:
            avatar_bytes = await resp.read()

    avatar = Image.open(io.BytesIO(avatar_bytes)).convert("RGBA")
    avatar = avatar.resize((110, 110))

    mask = Image.new("L", (110, 110), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, 110, 110), fill=255)
    avatar.putalpha(mask)

    spacing = 60
    pattern_speed = 4

    frame_index = 0

    for welcome_word in welcome_texts:

        # TYPEWRITER EFFECT
        for i in range(1, len(welcome_word) + 1):

            img = base_bg.copy()
            draw = ImageDraw.Draw(img)

            # Moving pattern
            pattern_layer = Image.new("RGBA", (width + spacing, height), (0, 0, 0, 0))
            p_draw = ImageDraw.Draw(pattern_layer)

            offset = frame_index * pattern_speed

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

            # Avatar
            img.paste(avatar, (60, 150), avatar)

            # Typed text
            typed_text = welcome_word[:i]
            draw.text((60, 60), typed_text, font=font_title, fill=(255, 255, 255))

            # User info
            draw.text((200, 150), username, font=font_user, fill=(255, 255, 255))
            draw.text((200, 200), member_count, font=font_small, fill=(220, 220, 255))
            draw.text((200, 230), join_time, font=font_small, fill=(220, 220, 255))

            # AS logo
            draw.text((60, height - 60), "AS", font=font_logo, fill=(255, 255, 255))

            frames.append(img)
            frame_index += 1

        # Pause on full word
        for _ in range(8):
            frames.append(frames[-1])
            frame_index += 1

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
