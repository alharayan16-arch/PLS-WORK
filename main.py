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

    font_title = ImageFont.truetype("NotoSans-Bold.ttf", 65)
    font_user = ImageFont.truetype("NotoSans-Regular.ttf", 38)
    font_small = ImageFont.truetype("NotoSans-Regular.ttf", 26)
    font_logo = ImageFont.truetype("Montserrat-Bold.ttf", 32)

    username = member.display_name
    member_count = f"Member #{member.guild.member_count}"
    join_time = datetime.datetime.now(datetime.UTC).strftime("%H:%M UTC")

    languages = [
        "Welcome",
        "مرحبا",
        "स्वागत है",
        "Willkommen",
        "欢迎",
        "Benvenuto"
    ]

    # Background
    base_bg = Image.new("RGBA", (width, height), (88, 0, 170, 255))
    bg_draw = ImageDraw.Draw(base_bg)

    for y in range(height):
        ratio = y / height
        r = int(88 * (1 - ratio))
        g = 0
        b = int(170 * (1 - ratio))
        bg_draw.line([(0, y), (width, y)], fill=(r, g, b, 255))

    # Avatar
    async with aiohttp.ClientSession() as session:
        async with session.get(member.display_avatar.url) as resp:
            avatar_bytes = await resp.read()

    avatar = Image.open(io.BytesIO(avatar_bytes)).convert("RGBA")
    avatar = avatar.resize((100, 100))

    mask = Image.new("L", (100, 100), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, 100, 100), fill=255)
    avatar.putalpha(mask)

    spacing = 60
    total_frames = 240  # smooth cycle

    cycle_length = 80        # frames per language
    typing_frames = 55       # slow smooth typing
    hold_frames = 25         # hold full word

    for frame in range(total_frames):

        img = base_bg.copy()
        draw = ImageDraw.Draw(img)

        # XO infinite movement
        pattern = Image.new("RGBA", (width + spacing, height), (0, 0, 0, 0))
        p_draw = ImageDraw.Draw(pattern)

        offset = (frame * 4) % spacing

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

        # -------- SLOW SMOOTH TYPING --------
        lang_index = (frame // cycle_length) % len(languages)
        text = languages[lang_index]

        frame_in_cycle = frame % cycle_length

        if frame_in_cycle < typing_frames:
            progress = frame_in_cycle / typing_frames
            char_count = int(progress * len(text))
            visible_text = text[:char_count]
        else:
            visible_text = text  # hold full word

        draw.text((60, 60),
                  visible_text,
                  font=font_title,
                  fill=(255, 255, 255))

        # Avatar
        img.paste(avatar, (60, 150), avatar)

        # User info
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

        # AS logo
        draw.text((60, height - 55),
                  "AS",
                  font=font_logo,
                  fill=(255, 255, 255))

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
    gif = await create_welcome_gif(ctx.author)
    await ctx.send(file=discord.File(gif))


bot.run(TOKEN)
