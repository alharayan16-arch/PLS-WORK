import discord
from discord.ext import commands
import os
import asyncio
from aiohttp import web
from PIL import Image, ImageDraw, ImageFont
import requests
import io

TOKEN = os.getenv("TOKEN")

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ==============================
# IMAGE GENERATION ENDPOINT
# ==============================

async def generate_image(request):
    try:
        data = await request.json()

        donator = data["donatorName"]
        raiser = data["raiserName"]
        amount = data["amount"]
        donator_avatar = data["donatorAvatar"]
        raiser_avatar = data["raiserAvatar"]

        img = Image.new("RGB", (1000, 300), "#2b2d31")
        draw = ImageDraw.Draw(img)

        # Download avatars
        d_avatar = Image.open(io.BytesIO(requests.get(donator_avatar).content)).resize((140, 140))
        r_avatar = Image.open(io.BytesIO(requests.get(raiser_avatar).content)).resize((140, 140))

        img.paste(d_avatar, (80, 80))
        img.paste(r_avatar, (780, 80))

        # Use your existing fonts
        font_big = ImageFont.truetype("Montserrat-Bold.ttf", 60)
        font_small = ImageFont.truetype("Montserrat-Regular.ttf", 30)

        draw.text((500, 110), f"{amount:,}", font=font_big, fill="#ff00ff", anchor="mm")
        draw.text((500, 170), "donated to", font=font_small, fill="white", anchor="mm")

        draw.text((150, 240), f"@{donator}", font=font_small, fill="white")
        draw.text((850, 240), f"@{raiser}", font=font_small, fill="white", anchor="rm")

        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)

        return web.Response(body=buffer.read(), content_type="image/png")

    except Exception as e:
        print("Image generation error:", e)
        return web.Response(status=500, text="Error generating image")


# ==============================
# DISCORD EVENTS
# ==============================

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Logged in as {bot.user}")


async def load_extensions():
    await bot.load_extension("giveaways")
    await bot.load_extension("welcome")
    await bot.load_extension("staff")
    await bot.load_extension("goodbye")


# ==============================
# MAIN
# ==============================

async def main():
    app = web.Application()
    app.router.add_post("/generate", generate_image)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 3000)
    await site.start()

    print("Web server started on port 3000")

    async with bot:
        await load_extensions()
        await bot.start(TOKEN)


asyncio.run(main())