

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


async def create_welcome_gif(member):
    width, height = 900, 350
    frames = []

    # ---- FONTS ----
    font_title = ImageFont.truetype("NotoSans-Bold.ttf", 65)
    font_user = ImageFont.truetype("NotoSans-Regular.ttf", 38)
    font_small = ImageFont.truetype("NotoSans-Regular.ttf", 26)
    font_logo = ImageFont.truetype("NotoSans-Bold.ttf", 45)
    moving_font = ImageFont.truetype("NotoSans-Regular.ttf", 28)

    username = member.display_name
    member_count = f"Member #{member.guild.member_count}"
    join_time = datetime.datetime.now(datetime.UTC).strftime("%H:%M UTC")

    languages = [
        "Welcome",
        "Willkommen",
        "Bienvenue",
        "Benvenuto",
        "Bienvenido",
    ]

    # -------- 3 COLOR DIAGONAL GRADIENT --------
    base_bg = Image.new("RGBA", (width, height))
    pixels = base_bg.load()

    color_top_left = (120, 0, 200)
    color_middle = (80, 0, 150)
    color_bottom_right = (20, 0, 60)

    for y in range(height):
        for x in range(width):

            ratio_x = x / width
            ratio_y = y / height

            blend1_r = int(color_top_left[0] * (1 - ratio_x) + color_middle[0] * ratio_x)
            blend1_g = int(color_top_left[1] * (1 - ratio_x) + color_middle[1] * ratio_x)
            blend1_b = int(color_top_left[2] * (1 - ratio_x) + color_middle[2] * ratio_x)

            final_r = int(blend1_r * (1 - ratio_y) + color_bottom_right[0] * ratio_y)
            final_g = int(blend1_g * (1 - ratio_y) + color_bottom_right[1] * ratio_y)
            final_b = int(blend1_b * (1 - ratio_y) + color_bottom_right[2] * ratio_y)

            pixels[x, y] = (final_r, final_g, final_b, 255)

    # -------- DOWNLOAD AVATAR --------
    async with aiohttp.ClientSession() as session:
        async with session.get(member.display_avatar.url) as resp:
            avatar_bytes = await resp.read()

    avatar = Image.open(io.BytesIO(avatar_bytes)).convert("RGBA")
    avatar = avatar.resize((100, 100))

    mask = Image.new("L", (100, 100), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, 100, 100), fill=255)
    avatar.putalpha(mask)

    # -------- ANIMATION SETTINGS --------
    spacing = 60
    total_frames = 240
    cycle_length = 80
    typing_frames = 55

    for frame in range(total_frames):

        img = base_bg.copy()
        draw = ImageDraw.Draw(img)

        # -------- XO INFINITE MOVEMENT --------
        pattern = Image.new("RGBA", (width + spacing, height), (0, 0, 0, 0))
        p_draw = ImageDraw.Draw(pattern)

        offset = (frame * 4) % spacing

        for y in range(0, height, spacing):
            for x in range(0, width + spacing, spacing):
                p_draw.text((x, y), "X",
                            font=moving_font,
                            fill=(255, 255, 255, 18))
                p_draw.text((x + 25, y + 25), "O",
                            font=moving_font,
                            fill=(255, 255, 255, 18))

        cropped = pattern.crop((offset, 0, offset + width, height))
        img = Image.alpha_composite(img, cropped)

        draw = ImageDraw.Draw(img)

        # -------- SMOOTH TYPING --------
        lang_index = (frame // cycle_length) % len(languages)
        text = languages[lang_index]

        frame_in_cycle = frame % cycle_length

        if frame_in_cycle < typing_frames:
            progress = frame_in_cycle / typing_frames
            char_count = int(progress * len(text))
            visible_text = text[:char_count]
        else:
            visible_text = text

        draw.text((60, 60),
                  visible_text,
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

        # -------- NEON AS --------
        base_x = 60
        base_y = height - 70

        # Glow layers
        for glow_radius in [8, 5, 3]:
            glow_layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
            glow_draw = ImageDraw.Draw(glow_layer)
            glow_draw.text((base_x, base_y),
                           "AS",
                           font=font_logo,
                           fill=(255, 255, 255, 120))
            glow_layer = glow_layer.filter(ImageFilter.GaussianBlur(glow_radius))
            img = Image.alpha_composite(img, glow_layer)

        draw = ImageDraw.Draw(img)

        # Main AS text
        draw.text((base_x, base_y),
                  "AS",
                  font=font_logo,
                  fill=(255, 255, 255))

        # -------- MOVING STUDIO TEXT --------
        moving_text = "STUDIO"

        text_width = draw.textlength(moving_text, font=moving_font)
        move_area = 220

        move_offset = (frame * 3) % (move_area + text_width)

        draw.text((base_x + 100 + move_offset - text_width,
                   base_y + 15),
                  moving_text,
                  font=moving_font,
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
