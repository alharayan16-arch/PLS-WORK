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
    width, height = 1000, 400
    frames = []

    font_title = ImageFont.truetype("Montserrat-Bold.ttf", 70)
    font_user = ImageFont.truetype("Montserrat-Regular.ttf", 40)
    font_small = ImageFont.truetype("Montserrat-Regular.ttf", 28)
    font_logo = ImageFont.truetype("Montserrat-Bold.ttf", 45)

    username = member.display_name
    member_count = f"Member #{member.guild.member_count}"
    join_time = datetime.datetime.now(datetime.UTC).strftime("%H:%M UTC")

    # Background (diagonal gradient)
    base_bg = Image.new("RGB", (width, height))
    bg_draw = ImageDraw.Draw(base_bg)

    for y in range(height):
        for x in range(width):
            ratio = (x + y) / (width + height)
            r = int(120 - ratio * 60)
            g = 0
            b = int(200 - ratio * 120)
            bg_draw.point((x, y), fill=(r, g, b))

    base_bg = base_bg.convert("RGBA")

    # Download avatar
    async with aiohttp.ClientSession() as session:
        async with session.get(member.display_avatar.url) as resp:
            avatar_bytes = await resp.read()

    avatar = Image.open(io.BytesIO(avatar_bytes)).convert("RGBA")
    avatar = avatar.resize((110, 110))

    mask = Image.new("L", (110, 110), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, 110, 110), fill=255)
    avatar.putalpha(mask)

    total_frames = 80

    for frame in range(total_frames):
        img = base_bg.copy()
        draw = ImageDraw.Draw(img)

        # TEXT
        draw.text((60, 60), "Welcome", font=font_title, fill=(255, 255, 255))
        draw.text((200, 150), username, font=font_user, fill=(255, 255, 255))
        draw.text((200, 200), member_count, font=font_small, fill=(230, 230, 255))
        draw.text((200, 230), join_time, font=font_small, fill=(230, 230, 255))

        img.paste(avatar, (60, 150), avatar)

        # -------- TRUE INFINITE STRIPES (AFTER AS ONLY) --------

        stripe_height = 60
        stripe_y = height - 80

        # Leave space for AS (avoid overlap)
        as_safe_zone_width = 140

        stripe_canvas_width = width * 2
        stripe_canvas = Image.new("RGBA", (stripe_canvas_width, height), (0, 0, 0, 0))
        s_draw = ImageDraw.Draw(stripe_canvas)

        stripe_spacing = 180
        stripe_width = 90

        for i in range(0, stripe_canvas_width, stripe_spacing):
            x = i + as_safe_zone_width
            s_draw.polygon([
                (x, stripe_y),
                (x + stripe_width, stripe_y),
                (x + stripe_width - 35, stripe_y + stripe_height),
                (x - 35, stripe_y + stripe_height)
            ], fill=(255, 255, 255, 210))  # Brighter white

        offset = (frame * 6) % stripe_spacing
        cropped = stripe_canvas.crop((offset, 0, offset + width, height))
        img = Image.alpha_composite(img, cropped)

        draw = ImageDraw.Draw(img)

        # -------- NEON AS --------
        as_x = 60
        as_y = height - 75

        for glow in [8, 5, 3]:
            glow_layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
            glow_draw = ImageDraw.Draw(glow_layer)
            glow_draw.text((as_x, as_y), "AS",
                           font=font_logo,
                           fill=(255, 255, 255, 120))
            glow_layer = glow_layer.filter(ImageFilter.GaussianBlur(glow))
            img = Image.alpha_composite(img, glow_layer)

        draw = ImageDraw.Draw(img)
        draw.text((as_x, as_y), "AS",
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
    gif = await create_welcome_gif(ctx.author)
    await ctx.send(file=discord.File(gif))


bot.run(TOKEN)
