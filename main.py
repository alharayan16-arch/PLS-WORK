import discord
from discord.ext import commands
import os
import asyncio
from aiohttp import web
from PIL import Image, ImageDraw, ImageFont
import aiohttp
import requests
import io

# =========================
# CONFIG
# =========================

TOKEN = os.getenv("TOKEN")

WEBHOOK_URL = "https://discord.com/api/webhooks/1474841301567410389/ZgQn4ISI1dNbTSfIu3vhd68BcmBUX6yX_XpAG6aNXM0zf1NOElEGJnkvcZQslGdkZFdn"

PORT = int(os.getenv("PORT", 3000))

# =========================
# DISCORD BOT
# =========================

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Logged in as {bot.user}")

# =========================
# IMAGE GENERATION ENDPOINT
# =========================

async def generate_image(request):
    try:
        data = await request.json()

        donator = data["donatorName"]
        raiser = data["raiserName"]
        amount = int(data["amount"])
        donator_avatar = data["donatorAvatar"]
        raiser_avatar = data["raiserAvatar"]

        # Create image
        img = Image.new("RGB", (1000, 300), "#2b2d31")
        draw = ImageDraw.Draw(img)

        # Download avatars
        d_avatar = Image.open(io.BytesIO(requests.get(donator_avatar).content)).resize((140, 140))
        r_avatar = Image.open(io.BytesIO(requests.get(raiser_avatar).content)).resize((140, 140))

        img.paste(d_avatar, (80, 80))
        img.paste(r_avatar, (780, 80))

        # Fonts
        font_big = ImageFont.load_default()
        font_small = ImageFont.load_default()

        # Text
        draw.text((500, 110), f"{amount:,}", font=font_big, fill="#ff00ff", anchor="mm")
        draw.text((500, 170), "donated to", font=font_small, fill="white", anchor="mm")

        draw.text((150, 240), f"@{donator}", font=font_small, fill="white")
        draw.text((850, 240), f"@{raiser}", font=font_small, fill="white", anchor="rm")

        # Save to memory
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)

        # Send to Discord webhook
        async with aiohttp.ClientSession() as session:
            form = aiohttp.FormData()
            form.add_field(
                "file",
                buffer,
                filename="donation.png",
                content_type="image/png"
            )
            await session.post(WEBHOOK_URL, data=form)

        return web.Response(text="Sent to Discord")

     except Exception as e:
        import traceback
        import traceback
        return web.Response(status=500, text=str(e))

# =========================
# START WEB SERVER
# =========================

async def start_webserver():
    app = web.Application()
    app.router.add_post("/generate", generate_image)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()

    print(f"Web server started on port {PORT}")

# =========================
# MAIN
# =========================

async def main():
    await start_webserver()

    async with bot:
        await bot.start(TOKEN)

asyncio.run(main())