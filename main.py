import discord
from discord.ext import commands
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import datetime
import aiohttp
import io
import os

TOKEN = os.getenv("TOKEN")

WELCOME_CHANNEL_ID = 1472224372382109905
GOODBYE_CHANNEL_ID = 1473690582756098231  # <-- PUT YOUR GOODBYE CHANNEL ID HERE

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")


# =====================================================
# WELCOME GIF
# =====================================================
async def create_welcome_gif(member):
    width, height = 1000, 400
    frames = []

    font_title = ImageFont.truetype("Montserrat-Bold.ttf", 70)
    font_user = ImageFont.truetype("Montserrat-Regular.ttf", 40)
    font_small = ImageFont.truetype("Montserrat-Regular.ttf", 28)
    font_logo = ImageFont.truetype("Montserrat-Bold.ttf", 110)
    font_link = ImageFont.truetype("Montserrat-Regular.ttf", 24)

    sequences = [
        ["W","WE","WEL","WELC","WELCO","WELCOM","WELCOME"],
        ["W","WI","WIL","WILL","WILLK","WILLKO","WILLKOM","WILLKOMM","WILLKOMME","WILLKOMMEN"],
        ["B","BE","BEN","BENV","BENVE","BENVEN","BENVENU","BENVENUT","BENVENUTO"],
    ]

    return await generate_gif(member, sequences)


# =====================================================
# GOODBYE GIF (DARK DRAMATIC VERSION)
# =====================================================
async def create_goodbye_gif(member):
    width, height = 1000, 400
    frames = []

    font_title = ImageFont.truetype("Montserrat-Bold.ttf", 70)
    font_user = ImageFont.truetype("Montserrat-Regular.ttf", 40)
    font_small = ImageFont.truetype("Montserrat-Regular.ttf", 28)
    font_logo = ImageFont.truetype("Montserrat-Bold.ttf", 110)

    sequences = [
        ["G","GO","GOO","GOOD","GOODB","GOODBY","GOODBYE"],
        ["A","AU","AUF","AUF ","AUF W","AUF WI","AUF WIE","AUF WIED","AUF WIEDE","AUF WIEDER","AUF WIEDERS","AUF WIEDERSE","AUF WIEDERSEH","AUF WIEDERSEHE","AUF WIEDERSEHEN"],
        ["A","AR","ARR","ARRI","ARRIV","ARRIVE","ARRIVED","ARRIVEDER","ARRIVEDERC","ARRIVEDERCI"],
    ]

    username = member.display_name
    member_count = f"Member #{member.guild.member_count}"
    current_time = datetime.datetime.now(datetime.timezone.utc).strftime("%H:%M UTC")

    # 🌑 DARKER DRAMATIC DIAGONAL BACKGROUND
    base_bg = Image.new("RGB", (width, height))
    bg_draw = ImageDraw.Draw(base_bg)

    for y in range(height):
        for x in range(width):
            ratio = (x + y) / (width + height)
            r = int(25 - ratio * 20)
            g = 0
            b = int(60 - ratio * 50)
            bg_draw.point((x, y), fill=(max(r,0), g, max(b,0)))

    base_bg = base_bg.convert("RGBA")

    # Avatar
    async with aiohttp.ClientSession() as session:
        async with session.get(member.display_avatar.url) as resp:
            avatar_bytes = await resp.read()

    avatar = Image.open(io.BytesIO(avatar_bytes)).convert("RGBA")
    avatar = avatar.resize((110, 110))

    mask = Image.new("L", (110, 110), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, 110, 110), fill=255)
    avatar.putalpha(mask)

    spacing = 60
    typing_speed = 6

    cycle_lengths = [len(seq) * typing_speed for seq in sequences]
    total_cycle = sum(cycle_lengths)
    total_frames = total_cycle + 30

    for frame in range(total_frames):
        img = base_bg.copy()
        draw = ImageDraw.Draw(img)

        # 🌑 DARK XO Pattern (more subtle)
        pattern_layer = Image.new("RGBA", (width * 2, height), (0, 0, 0, 0))
        p_draw = ImageDraw.Draw(pattern_layer)

        for y in range(0, height, spacing):
            for x in range(0, width * 2, spacing):
                p_draw.text((x, y), "X", font=font_small, fill=(255, 255, 255, 35))
                p_draw.text((x + 25, y + 25), "O", font=font_small, fill=(255, 255, 255, 35))

        offset = (frame * 4) % spacing
        cropped_pattern = pattern_layer.crop((offset, 0, offset + width, height))
        img = Image.alpha_composite(img, cropped_pattern)

        draw = ImageDraw.Draw(img)

        # Typing animation
        cycle_frame = frame % total_cycle
        cumulative = 0

        for seq, seq_length in zip(sequences, cycle_lengths):
            if cycle_frame < cumulative + seq_length:
                local_frame = cycle_frame - cumulative
                letter_index = min(len(seq)-1, local_frame // typing_speed)
                display_text = seq[letter_index]
                break
            cumulative += seq_length

        draw.text((60, 60), display_text, font=font_title, fill=(255, 255, 255))

        # User info
        draw.text((200, 150), username, font=font_user, fill=(255, 255, 255))
        draw.text((200, 200), member_count, font=font_small, fill=(200, 200, 255))
        draw.text((200, 230), current_time, font=font_small, fill=(200, 200, 255))

        img.paste(avatar, (60, 150), avatar)

        # Moving stripes (unchanged)
        stripe_canvas = Image.new("RGBA", (width * 2, height), (0, 0, 0, 0))
        s_draw = ImageDraw.Draw(stripe_canvas)

        stripe_y = height - 80
        stripe_height = 60
        stripe_spacing = 180
        stripe_width = 90

        for i in range(0, width * 2, stripe_spacing):
            x = i
            s_draw.polygon([
                (x, stripe_y),
                (x + stripe_width, stripe_y),
                (x + stripe_width - 35, stripe_y + stripe_height),
                (x - 35, stripe_y + stripe_height)
            ], fill=(255, 255, 255, 200))

        stripe_offset = (frame * 6) % stripe_spacing
        cropped_stripes = stripe_canvas.crop(
            (stripe_spacing - stripe_offset, 0,
             stripe_spacing - stripe_offset + width, height)
        )

        img = Image.alpha_composite(img, cropped_stripes)
        draw = ImageDraw.Draw(img)

        # AS Glow Logo (kept)
        letter_spacing = -8
        a_width = draw.textlength("A", font=font_logo)
        s_width = draw.textlength("S", font=font_logo)
        as_total_width = a_width + s_width + letter_spacing

        as_x = width - as_total_width - 140
        as_y = 40

        for glow in [45, 30, 15]:
            glow_layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
            glow_draw = ImageDraw.Draw(glow_layer)

            glow_draw.text((as_x, as_y - 12), "A",
                           font=font_logo,
                           fill=(255, 255, 255, 220))

            glow_draw.text((as_x + a_width + letter_spacing, as_y),
                           "S",
                           font=font_logo,
                           fill=(255, 255, 255, 220))

            glow_layer = glow_layer.filter(ImageFilter.GaussianBlur(glow))
            img = Image.alpha_composite(img, glow_layer)

        draw = ImageDraw.Draw(img)

        draw.text((as_x, as_y - 12), "A", font=font_logo, fill=(255, 255, 255))
        draw.text((as_x + a_width + letter_spacing, as_y),
                  "S", font=font_logo, fill=(255, 255, 255))

        frames.append(img)

    gif_path = f"goodbye_{member.id}.gif"

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