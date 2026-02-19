import discord
from discord.ext import commands
from PIL import Image, ImageDraw, ImageFont
import datetime
import aiohttp
import io
import os
import random
import json
import asyncio

TOKEN = os.getenv("TOKEN")

WELCOME_CHANNEL_ID = 1472224372382109905
STAFF_LOG_CHANNEL_ID = 1473910880264519730
SUPPORT_CHANNEL_ID = 1472228682566340842

GIVEAWAY_FILE = "giveaways.json"

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# =========================
# STORAGE
# =========================

def load_giveaways():
    if not os.path.exists(GIVEAWAY_FILE):
        return {}
    with open(GIVEAWAY_FILE, "r") as f:
        return json.load(f)

def save_giveaways(data):
    with open(GIVEAWAY_FILE, "w") as f:
        json.dump(data, f, indent=4)

# =========================
# READY
# =========================

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Logged in as {bot.user}")

    data = load_giveaways()
    for giveaway_id, giveaway in data.items():
        if not giveaway.get("ended"):
            remaining = giveaway["end_time"] - int(datetime.datetime.utcnow().timestamp())
            if remaining > 0:
                bot.loop.create_task(schedule_end(giveaway_id, remaining))

# =========================
# WELCOME SYSTEM
# =========================

async def create_welcome_gif(member):
    width, height = 900, 400
    img = Image.new("RGB", (width, height), (60, 0, 120))
    draw = ImageDraw.Draw(img)

    font_title = ImageFont.truetype("Montserrat-Bold.ttf", 60)
    font_small = ImageFont.truetype("Montserrat-Regular.ttf", 30)

    draw.text((50, 50), "WELCOME", font=font_title, fill=(255, 255, 255))
    draw.text((50, 150), member.display_name, font=font_small, fill=(255, 255, 255))

    path = f"welcome_{member.id}.png"
    img.save(path)
    return path

@bot.event
async def on_member_join(member):
    channel = bot.get_channel(WELCOME_CHANNEL_ID)
    gif = await create_welcome_gif(member)
    await channel.send(file=discord.File(gif))

# =========================
# GIVEAWAY SYSTEM
# =========================

class GiveawayView(discord.ui.View):
    def __init__(self, giveaway_id):
        super().__init__(timeout=None)
        self.giveaway_id = giveaway_id

    @discord.ui.button(label="🎉 Enter Giveaway (0)", style=discord.ButtonStyle.primary)
    async def enter(self, interaction: discord.Interaction, button: discord.ui.Button):

        data = load_giveaways()
        giveaway = data[self.giveaway_id]

        if interaction.user.id in giveaway["entries"]:
            await interaction.response.send_message("❌ You already entered!", ephemeral=True)
            return

        giveaway["entries"].append(interaction.user.id)
        save_giveaways(data)

        button.label = f"🎉 Enter Giveaway ({len(giveaway['entries'])})"
        await interaction.message.edit(view=self)

        await interaction.response.send_message("✅ You entered!", ephemeral=True)

async def schedule_end(giveaway_id, delay):
    await asyncio.sleep(delay)
    await end_giveaway(giveaway_id)

async def end_giveaway(giveaway_id):
    data = load_giveaways()
    giveaway = data[giveaway_id]
    channel = bot.get_channel(giveaway["channel_id"])
    staff_channel = bot.get_channel(STAFF_LOG_CHANNEL_ID)

    winners = random.sample(
        giveaway["entries"],
        min(giveaway["winners"], len(giveaway["entries"]))
    )

    giveaway["last_winners"] = winners
    giveaway["ended"] = True
    giveaway["rerolls"] = 0
    save_giveaways(data)

    mentions = []

    for winner_id in winners:
        member = channel.guild.get_member(winner_id)
        if member:
            mentions.append(member.mention)
            try:
                embed = discord.Embed(
                    title="🎉 YOU WON! 🎉",
                    description=f"🏆 Prize: **{giveaway['prize']}**\n\n🎫 Claim in <#{SUPPORT_CHANNEL_ID}>",
                    color=discord.Color.purple()
                )
                await member.send(embed=embed)
            except:
                pass

    embed = discord.Embed(
        title="🎉 GIVEAWAY ENDED! 🎉",
        description=(
            f"🏆 Prize: **{giveaway['prize']}**\n"
            f"👥 Total Entries: {len(giveaway['entries'])}\n"
            f"🥇 Winner(s): {', '.join(mentions)}\n\n"
            f"🎫 Create a ticket in <#{SUPPORT_CHANNEL_ID}>"
        ),
        color=discord.Color.purple()
    )

    await channel.send(embed=embed)

    if staff_channel:
        await staff_channel.send(
            f"🏆 Giveaway ended | Winners: {', '.join(mentions)}"
        )

@bot.tree.command(name="giveaway", description="Start a giveaway")
async def giveaway(interaction: discord.Interaction, duration: int, winners: int, prize: str):

    if not interaction.user.guild_permissions.manage_guild:
        await interaction.response.send_message("❌ Need Manage Server permission.", ephemeral=True)
        return

    end_time = datetime.datetime.utcnow() + datetime.timedelta(minutes=duration)
    giveaway_id = str(interaction.id)

    embed = discord.Embed(
        title="✨ ARAB’S STUDIO GIVEAWAY ✨",
        description=(
            f"🎁 Prize: **{prize}**\n"
            f"👥 Winners: {winners}\n\n"
            f"⏰ Ends: <t:{int(end_time.timestamp())}:R>"
        ),
        color=discord.Color.purple()
    )

    view = GiveawayView(giveaway_id)
    await interaction.response.send_message(embed=embed, view=view)
    message = await interaction.original_response()

    data = load_giveaways()
    data[giveaway_id] = {
        "channel_id": interaction.channel.id,
        "message_id": message.id,
        "prize": prize,
        "winners": winners,
        "end_time": int(end_time.timestamp()),
        "entries": [],
        "ended": False,
        "rerolls": 0
    }
    save_giveaways(data)

    bot.loop.create_task(schedule_end(giveaway_id, duration * 60))

# =========================
# SERVER STATS IMAGE CARD
# =========================

@bot.tree.command(name="serverstats", description="View server statistics")
async def serverstats(interaction: discord.Interaction):

    guild = interaction.guild
    data = load_giveaways()
    active_giveaways = sum(1 for g in data.values() if not g.get("ended"))

    width, height = 900, 450
    img = Image.new("RGB", (width, height))
    draw = ImageDraw.Draw(img)

    for y in range(height):
        for x in range(width):
            ratio = (x + y) / (width + height)
            r = int(90 - ratio * 40)
            g = 0
            b = int(150 - ratio * 60)
            draw.point((x, y), fill=(r, g, b))

    font_title = ImageFont.truetype("Montserrat-Bold.ttf", 55)
    font_stat = ImageFont.truetype("Montserrat-Regular.ttf", 32)

    draw.text((50, 40), "ARAB'S STUDIO STATS", font=font_title, fill=(255, 255, 255))

    draw.text((60, 140), f"👥 Members: {guild.member_count}", font=font_stat, fill=(255, 255, 255))
    draw.text((60, 190), f"🟢 Online: {sum(m.status != discord.Status.offline for m in guild.members)}", font=font_stat, fill=(255, 255, 255))
    draw.text((60, 240), f"🚀 Boost Level: {guild.premium_tier}", font=font_stat, fill=(255, 255, 255))
    draw.text((60, 290), f"💎 Boost Count: {guild.premium_subscription_count}", font=font_stat, fill=(255, 255, 255))
    draw.text((60, 340), f"🎉 Active Giveaways: {active_giveaways}", font=font_stat, fill=(255, 255, 255))

    path = f"serverstats_{guild.id}.png"
    img.save(path)

    await interaction.response.send_message(file=discord.File(path))

bot.run(TOKEN)
