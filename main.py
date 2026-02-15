import discord
from discord.ext import commands
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import datetime
import aiohttp
import io
import os
import math

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
    width, height = 1000, 400
    frames = []

    # -------- FONTS --------
    font_title = ImageFont.truetype("Montserrat-Bold.ttf", 70)
    font_user = ImageFont.truetype("Montserrat-Regular.ttf", 40)
    font_small = ImageFont.truetype("Montserrat-Regular.ttf", 28)
    font_logo = ImageFont.truetype("Montserrat-Bold.ttf", 90)
    font_link = ImageFont.truetype("Montserrat-Regular.ttf", 24)

    username = member.display_name
    member_count = f"Member #{member.guild.member_count}"
    join_time = datetime.datetime.now(datetime.timezone.utc).strftime("%H:%M UTC")

    # -------- WELCOME LANGUAGES --------
    welcomes = [
        "WELCOME",
        "WILLKOMMEN",
        "BENVENUTO"
    ]

    # -------- AVATAR DOWNLOAD --------
    async with aiohttp.ClientSession() as session:
        async with session.get(member.display_avatar.url) as resp:
            avatar_bytes = await resp.read()

    avatar = Image.open(io.BytesIO(avatar_bytes)).convert("RGBA")
    avatar = avatar.resize((110, 110))

    mask = Image.new("L", (110, 110), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, 110, 110), fill=255)
    avatar.putalpha(mask)

    # -------- SMOOTH DARK BACKGROUND --------
    base = Image.new("RGB", (width, height), (35, 0, 60))
    gradient = Image.new("RGBA", (width, height))
    gdraw = ImageDraw.Draw(gradient)

    for y in range(height):
        r = int(80 - (y / height) * 40)
        b = int(150 - (y / height) * 90)
        gdraw.line([(0, y), (width, y)], fill=(r, 0, b, 255))

    base = Image.alpha_composite(base.convert("RGBA"), gradient)

    spacing = 55
    total_frames = 120

    for frame in range(total_frames):

        img = base.copy()
        draw = ImageDraw.Draw(img)

        # -------- XO PATTERN (FASTER, SMOOTH) --------
        pattern_layer = Image.new("RGBA", (width + spacing, height), (0, 0, 0, 0))
        p_draw = ImageDraw.Draw(pattern_layer)

        offset = (frame * 6) % spacing

        for y in range(0, height, spacing):
            for x in range(0, width + spacing, spacing):
                p_draw.text((x, y), "X", font=font_small, fill=(255, 255, 255, 40))
                p_draw.text((x + 25, y + 25), "O", font=font_small, fill=(255, 255, 255, 40))

        cropped = pattern_layer.crop((offset, 0, offset + width, height))
        img = Image.alpha_composite(img, cropped)
        draw = ImageDraw.Draw(img)

        # -------- STRIPES LEFT → RIGHT --------
        stripe_layer = Image.new("RGBA", (width * 2, height), (0, 0, 0, 0))
        sdraw = ImageDraw.Draw(stripe_layer)

        stripe_height = 60
        stripe_y = height - 80
        stripe_spacing = 160

        for i in range(0, width * 2, stripe_spacing):
            sdraw.polygon([
                (i, stripe_y),
                (i + 80, stripe_y),
                (i + 50, stripe_y + stripe_height),
                (i - 30, stripe_y + stripe_height)
            ], fill=(255, 255, 255, 210))

        stripe_offset = (frame * 8) % stripe_spacing
        cropped_stripes = stripe_layer.crop((stripe_offset, 0, stripe_offset + width, height))
        img = Image.alpha_composite(img, cropped_stripes)

        # -------- LANGUAGE TYPING --------
        cycle_length = 40
        typing_speed = 3

        lang_index = (frame // cycle_length) % len(welcomes)
        full_text = welcomes[lang_index]

        frame_in_cycle = frame % cycle_length
        letters_to_show = min(len(full_text), frame_in_cycle // typing_speed)

        welcome_text = full_text[:letters_to_show]

        draw = ImageDraw.Draw(img)
        draw.text((60, 60), welcome_text, font=font_title, fill=(255, 255, 255))

        # -------- USER INFO --------
        img.paste(avatar, (60, 150), avatar)
        draw.text((200, 150), username, font=font_user, fill=(255, 255, 255))
        draw.text((200, 200), member_count, font=font_small, fill=(220, 220, 255))
        draw.text((200, 230), join_time, font=font_small, fill=(220, 220, 255))

        # -------- GLOWING AS --------
        as_text = "AS"
        as_bbox = draw.textbbox((0, 0), as_text, font=font_logo)
        as_width = as_bbox[2] - as_bbox[0]

        as_x = width - as_width - 80
        as_y = 40

        # Glow layer
        glow = Image.new("RGBA", img.size, (0, 0, 0, 0))
        gdraw = ImageDraw.Draw(glow)

        for i in range(8):
            gdraw.text((as_x - i, as_y - i), as_text, font=font_logo, fill=(255, 255, 255, 40))
            gdraw.text((as_x + i, as_y + i), as_text, font=font_logo, fill=(255, 255, 255, 40))

        img = Image.alpha_composite(img, glow)
        draw = ImageDraw.Draw(img)
        draw.text((as_x, as_y), as_text, font=font_logo, fill=(255, 255, 255))

        # -------- DISCORD LINK --------
        link_text = "https://discord.gg/arabsstudio"

        link_bbox = draw.textbbox((0, 0), link_text, font=font_link)
        link_width = link_bbox[2] - link_bbox[0]

        link_x = as_x + (as_width // 2) - (link_width // 2) - 60

        draw.text((link_x, as_y + 110),
                  link_text,
                  font=font_link,
                  fill=(255, 255, 255, 160))

        frames.append(img.convert("P", palette=Image.ADAPTIVE))

    gif_path = f"welcome_{member.id}.gif"

    frames[0].save(
        gif_path,
        save_all=True,
        append_images=frames[1:],
        duration=35,
        loop=0,
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
    member = ctx.author

    gif = await create_welcome_gif(member)

    await ctx.send(
        content=f"{member.mention}, Welcome to Arab’s Studio — we’re glad to have you here!",
        file=discord.File(gif)
    )


bot.run(TOKEN)

