import discord
from discord.ext import commands
import os
import asyncio
from aiohttp import web
from PIL import Image, ImageDraw, ImageFont
import aiohttp
import requests
import io
import traceback

# =========================
# CONFIG
# =========================

TOKEN = os.getenv("TOKEN")
WEBHOOK_URL = "YOUR_WEBHOOK_URL_HERE"  # optional, replace if needed

# =========================
# DISCORD BOT SETUP
# =========================

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# =========================
# LOAD COGS
# =========================

async def load_extensions():
    await bot.load_extension("welcome")
    await bot.load_extension("goodbye")

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    print("Bot is ready.")

# =========================
# IMAGE GENERATION ENDPOINT
# =========================

async def generate_image(request):
    try:
        data = await request.json()
        print("RECEIVED DATA:", data)

        donator = data["donatorName"]
        raiser = data["raiserName"]
        amount = int(data["amount"])
        donator_avatar = data["donatorAvatar"]
        raiser_avatar = data["raiserAvatar"]

        # Canvas
        width, height = 1000, 360
        img = Image.new("RGB", (width, height), "#1e1f22")
        draw = ImageDraw.Draw(img)

        # Card
        margin = 40
        card = Image.new("RGB", (width - 80, height - 80), "#2b2d31")
        img.paste(card, (margin, margin))

        # Accent bar
        draw.rectangle(
            [(margin, margin), (margin + 8, height - margin)],
            fill="#ff00ff"
        )

        # Download avatars
        d_avatar = Image.open(io.BytesIO(requests.get(donator_avatar).content)).resize((160, 160))
        r_avatar = Image.open(io.BytesIO(requests.get(raiser_avatar).content)).resize((160, 160))

        # Circular mask
        mask = Image.new("L", (160, 160), 0)
        ImageDraw.Draw(mask).ellipse((0, 0, 160, 160), fill=255)

        # Pink borders
        border = Image.new("RGB", (180, 180), "#ff00ff")
        border_mask = Image.new("L", (180, 180), 0)
        ImageDraw.Draw(border_mask).ellipse((0, 0, 180, 180), fill=255)

        img.paste(border, (120, 90), border_mask)
        img.paste(border, (700, 90), border_mask)

        img.paste(d_avatar, (130, 100), mask)
        img.paste(r_avatar, (710, 100), mask)

        # Fonts
        try:
            font_big = ImageFont.truetype("Montserrat-Bold.ttf", 70)
            font_mid = ImageFont.truetype("Montserrat-Bold.ttf", 45)
            font_small = ImageFont.truetype("Montserrat-Regular.ttf", 28)
        except:
            font_big = ImageFont.load_default()
            font_mid = ImageFont.load_default()
            font_small = ImageFont.load_default()

        # Text
        draw.text((500, 140), f"{amount:,}",
                  font=font_big, fill="#ff00ff", anchor="mm")

        draw.text((500, 200), "donated to",
                  font=font_mid, fill="white", anchor="mm")

        draw.text((210, 300), f"@{donator}",
                  font=font_small, fill="white", anchor="mm")

        draw.text((790, 300), f"@{raiser}",
                  font=font_small, fill="white", anchor="mm")

        draw.text((200, 325),
                  "Donated on • Today",
                  font=font_small, fill="#b9bbbe")

        # Save image to buffer
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)

        # Send to webhook (optional)
        async with aiohttp.ClientSession() as session:
            form = aiohttp.FormData()
            form.add_field(
                "file",
                buffer,
                filename="donation.png",
                content_type="image/png"
            )
            response = await session.post(WEBHOOK_URL, data=form)
            print("Webhook status:", response.status)

        return web.Response(text="Donation sent!")

    except Exception:
        print("ERROR TRACE:")
        traceback.print_exc()
        return web.Response(status=500, text="Internal Server Error")

# =========================
# START WEB SERVER
# =========================

async def start_webserver():
    app = web.Application()
    app.router.add_post("/generate", generate_image)

    runner = web.AppRunner(app)
    await runner.setup()

    port = int(os.environ.get("PORT", 8000))
    site = web.TCPSite(runner, "0.0.0.0", port)

    await site.start()
    print(f"Web server started on port {port}")

# =========================
# MAIN STARTUP
# =========================

async def main():
    # Start web server in background
    asyncio.create_task(start_webserver())

    # Load cogs
    await load_extensions()

    # Start Discord bot
    await bot.start(TOKEN)

if __name__ == "__main__":
    asyncio.run(main())