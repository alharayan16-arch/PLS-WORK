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

    font_title = ImageFont.truetype("NotoSans-Bold.ttf", 65)
    font_user = ImageFont.truetype("NotoSans-Regular.ttf", 38)
    font_small = ImageFont.truetype("NotoSans-Regular.ttf", 26)
    font_logo = ImageFont.truetype("NotoSans-Bold.ttf", 55)
    pattern_font = ImageFont.truetype("NotoSans-Regular.ttf", 28)

    username = member.display_name
    member_count = f"Member #{member.guild.member_count}"
    join_time = datetime.datetime.now(datetime.UTC).strftime("%H:%M UTC")

    languages = ["Welcome", "Willkommen", "Bienvenue", "Benvenuto"]

    # ----- DIAGONAL GRADIENT BACKGROUND -----
    base = Image.new("RGBA", (width, height))
    px = base.load()

    c1 = (130, 0, 220)
    c2 = (80, 0, 150)
    c3 = (15, 0, 60)

    for y in range(height):
        for x in range(width):
            rx = x / width
            ry = y / height

            r1 = int(c1[0] * (1 - rx) + c2[0] * rx)
            g1 = int(c1[1] * (1 - rx) + c2[1] * rx)
            b1 = int(c1[2] * (1 - rx) + c2[2] * rx)

            r = int(r1 * (1 - ry) + c3[0] * ry)
            g = int(g1 * (1 - ry) + c3[1] * ry)
            b = int(b1 * (1 - ry) + c3[2] * ry)

            px[x, y] = (r, g, b, 255)

    # ----- AVATAR -----
    async with aiohttp.ClientSession() as session:
        async with session.get(member.display_avatar.url) as resp:
            avatar_bytes = await resp.read()

    avatar = Image.open(io.BytesIO(avatar_bytes)).convert("RGBA")
    avatar = avatar.resize((100, 100))

    mask = Image.new("L", (100, 100), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, 100, 100), fill=255)
    avatar.putalpha(mask)

    total_frames = 200
    spacing = 60

    for frame in range(total_frames):

        img = base.copy()
        draw = ImageDraw.Draw(img)

        # ----- XO MOVEMENT -----
        pattern_layer = Image.new("RGBA", (width + spacing, height), (0, 0, 0, 0))
        p_draw = ImageDraw.Draw(pattern_layer)

        offset = (frame * 3) % spacing

        for y in range(0, height, spacing):
            for x in range(0, width + spacing, spacing):
                p_draw.text((x, y), "X",
                            font=pattern_font,
                            fill=(255, 255, 255, 18))
                p_draw.text((x + 25, y + 25), "O",
                            font=pattern_font,
                            fill=(255, 255, 255, 18))

        cropped = pattern_layer.crop((offset, 0, offset + width, height))
        img = Image.alpha_composite(img, cropped)

        draw = ImageDraw.Draw(img)

        # ----- MOVING DIAGONAL STRIPES (LEFT → RIGHT) -----
        stripe_layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        s_draw = ImageDraw.Draw(stripe_layer)

        stripe_offset = (frame * 6) % 400

        for i in range(-400, width + 400, 200):
            x1 = i + stripe_offset
            s_draw.polygon([
                (x1, 0),
                (x1 + 80, 0),
                (x1 - 40, height),
                (x1 - 120, height)
            ], fill=(255, 255, 255, 35))

        # DO NOT OVERLAP AS AREA
        stripe_layer = stripe_layer.crop((150, 0, width, height))
        img.paste(stripe_layer, (150, 0), stripe_layer)

        draw = ImageDraw.Draw(img)

        # ----- TYPING WELCOME -----
        text = languages[(frame // 60) % len(languages)]
        char_count = min(len(text), frame % 60)
        draw.text((60, 60),
                  text[:char_count],
                  font=font_title,
                  fill=(255, 255, 255))

        # ----- AVATAR + INFO -----
        img.paste(avatar, (60, 150), avatar)

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

        # ----- NEON WHITE GLOW AS -----
        as_x = 60
        as_y = height - 80

        for glow in [12, 8, 5]:
            glow_layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
            g_draw = ImageDraw.Draw(glow_layer)
            g_draw.text((as_x, as_y),
                        "AS",
                        font=font_logo,
                        fill=(255, 255, 255, 120))
            glow_layer = glow_layer.filter(ImageFilter.GaussianBlur(glow))
            img = Image.alpha_composite(img, glow_layer)

        draw = ImageDraw.Draw(img)
        draw.text((as_x, as_y),
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
