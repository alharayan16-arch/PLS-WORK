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

    # Fonts
    font_title = ImageFont.truetype("Montserrat-Bold.ttf", 70)
    font_user = ImageFont.truetype("Montserrat-Regular.ttf", 40)
    font_small = ImageFont.truetype("Montserrat-Regular.ttf", 28)
    font_logo = ImageFont.truetype("Montserrat-Bold.ttf", 55)

    languages = [
        "Welcome",
        "Willkommen",
        "Benvenuto",
        "欢迎"
    ]

    username = member.display_name
    member_count = f"Member #{member.guild.member_count}"
    join_time = datetime.datetime.utcnow().strftime("%H:%M UTC")

    # Download avatar once
    async with aiohttp.ClientSession() as session:
        async with session.get(member.display_avatar.url) as resp:
            avatar_bytes = await resp.read()

    avatar = Image.open(io.BytesIO(avatar_bytes)).convert("RGBA")
    avatar = avatar.resize((110, 110))

    mask = Image.new("L", (110, 110), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, 110, 110), fill=255)
    avatar.putalpha(mask)

    total_frames = 60

    for frame in range(total_frames):
        # ---------- DIAGONAL GRADIENT ----------
        bg = Image.new("RGB", (width, height))
        draw_bg = ImageDraw.Draw(bg)

        for y in range(height):
            for x in range(width):
                ratio = (x + y) / (width + height)
                r = int(120 * (1 - ratio))
                g = 0
                b = int(200 * (1 - ratio))
                draw_bg.point((x, y), fill=(r, g, b))

        img = bg.convert("RGBA")
        draw = ImageDraw.Draw(img)

        # ---------- XO PATTERN (INFINITE RIGHT → LEFT) ----------
        pattern_layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
        p_draw = ImageDraw.Draw(pattern_layer)

        spacing = 60
        offset = (frame * 4) % spacing

        for y in range(0, height, spacing):
            for x in range(-spacing, width + spacing, spacing):
                px = x - offset
                p_draw.text((px, y), "X",
                            font=font_small,
                            fill=(255, 255, 255, 20))
                p_draw.text((px + 25, y + 25), "O",
                            font=font_small,
                            fill=(255, 255, 255, 20))

        img = Image.alpha_composite(img, pattern_layer)
        draw = ImageDraw.Draw(img)

        # ---------- TYPING LANGUAGE ----------
        cycle_length = 60
        lang_index = (frame // cycle_length) % len(languages)
        text = languages[lang_index]

        frame_in_cycle = frame % cycle_length
        typing_frames = 33

        if frame_in_cycle < typing_frames:
            progress = frame_in_cycle / typing_frames
            char_count = int(progress * len(text))
            visible_text = text[:char_count]
        else:
            visible_text = text

        # ---------- TEXT ----------
        draw.text((60, 60), visible_text,
                  font=font_title,
                  fill=(255, 255, 255))

        img.paste(avatar, (60, 150), avatar)

        draw.text((200, 150), username,
                  font=font_user,
                  fill=(255, 255, 255))

        draw.text((200, 200), member_count,
                  font=font_small,
                  fill=(220, 220, 255))

        draw.text((200, 230), join_time,
                  font=font_small,
                  fill=(220, 220, 255))

        # ---------- WHITE MOVING STRIPES (AS LEVEL ONLY) ----------
        stripe_layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
        s_draw = ImageDraw.Draw(stripe_layer)

        stripe_height = 55
        stripe_y = height - 70
        stripe_offset = (frame * 6) % 200

        for i in range(-200, width + 200, 140):
            x = i + stripe_offset
            s_draw.polygon([
                (x, stripe_y),
                (x + 60, stripe_y),
                (x + 20, stripe_y + stripe_height),
                (x - 40, stripe_y + stripe_height)
            ], fill=(255, 255, 255, 130))

        img = Image.alpha_composite(img, stripe_layer)

        # ---------- NEON GLOW AS ----------
        glow_layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
        g_draw = ImageDraw.Draw(glow_layer)

        as_position = (60, height - 70)

        g_draw.text(as_position,
                    "AS",
                    font=font_logo,
                    fill=(255, 255, 255, 255))

        glow_layer = glow_layer.filter(ImageFilter.GaussianBlur(8))
        img = Image.alpha_composite(img, glow_layer)

        draw = ImageDraw.Draw(img)
        draw.text(as_position,
                  "AS",
                  font=font_logo,
                  fill=(255, 255, 255))

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
    member = ctx.author
    gif = await create_welcome_gif(member)

    await ctx.send(
        file=discord.File(gif)
    )


bot.run(TOKEN)
