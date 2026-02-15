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

    # --------- CLEAN SOLID BACKGROUND ----------
    base_bg = Image.new("RGB", (width, height), (75, 0, 150))  # EXACT purple

    # Dark fade bottom overlay (no lines)
    fade = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    fade_draw = ImageDraw.Draw(fade)

    for y in range(height):
        alpha = int(180 * (y / height))
        fade_draw.line([(0, y), (width, y)], fill=(0, 0, 0, alpha))

    base_bg = Image.alpha_composite(base_bg.convert("RGBA"), fade)
    base_bg = base_bg.filter(ImageFilter.GaussianBlur(1))

    # Download avatar once
    async with aiohttp.ClientSession() as session:
        async with session.get(member.display_avatar.url) as resp:
            avatar_bytes = await resp.read()

    avatar = Image.open(io.BytesIO(avatar_bytes)).convert("RGBA")
    avatar = avatar.resize((110, 110))

    mask = Image.new("L", (110, 110), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, 110, 110), fill=255)
    avatar.putalpha(mask)

    spacing = 60
    total_frames = spacing  # seamless loop

    for frame in range(total_frames):
        img = base_bg.copy()
        draw = ImageDraw.Draw(img)

        # --------- FASTER RIGHT → LEFT PATTERN ----------
        pattern_layer = Image.new("RGBA", (width + spacing, height), (0, 0, 0, 0))
        p_draw = ImageDraw.Draw(pattern_layer)

        offset = frame * 3  # SPEED INCREASED

        for y in range(0, height, spacing):
            for x in range(0, width + spacing, spacing):
                p_draw.text((x, y),
                            "X",
                            font=font_logo,
                            fill=(255, 255, 255, 18))
                p_draw.text((x + 25, y + 25),
                            "O",
                            font=font_logo,
                            fill=(255, 255, 255, 18))

        cropped_pattern = pattern_layer.crop((offset % spacing, 0,
                                              offset % spacing + width, height))

        img = Image.alpha_composite(img, cropped_pattern)
        draw = ImageDraw.Draw(img)

        # --------- AVATAR ----------
        img.paste(avatar, (60, 150), avatar)

        # --------- TEXT ----------
        draw.text((60, 60), "Welcome", font=font_title, fill=(255, 255, 255))
        draw.text((200, 150), username, font=font_user, fill=(255, 255, 255))
        draw.text((200, 200), member_count, font=font_small, fill=(220, 220, 255))
        draw.text((200, 230), join_time, font=font_small, fill=(220, 220, 255))

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

    await ctx.send(
        content=f"{member.mention}, Welcome to Arab’s Studio — we’re glad to have you here!",
        file=discord.File(gif)
    )


bot.run(TOKEN)
