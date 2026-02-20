import discord
from discord.ext import commands
import os

TOKEN = os.getenv("TOKEN")

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Logged in as {bot.user}")

async def load_extensions():
    await bot.load_extension("giveaways")
    await bot.load_extension("welcome")

async def main():
    async with bot:
        await load_extensions()
        await bot.start(TOKEN)

import asyncio
asyncio.run(main())