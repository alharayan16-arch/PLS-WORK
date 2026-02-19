import discord
from discord.ext import commands
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import datetime
import os
import random
import json
import asyncio

TOKEN = os.getenv("TOKEN")

SUPPORT_CHANNEL_ID = 1472228682566340842
GIVEAWAY_FILE = "giveaways.json"

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# ================= STORAGE =================

def load_giveaways():
    if not os.path.exists(GIVEAWAY_FILE):
        return {}
    with open(GIVEAWAY_FILE, "r") as f:
        return json.load(f)

def save_giveaways(data):
    with open(GIVEAWAY_FILE, "w") as f:
        json.dump(data, f, indent=4)

# ================= READY =================

@bot.event
async def on_ready():
    await bot.tree.sync()
    print("✅ Slash commands synced globally.")
    print(f"Logged in as {bot.user}")

# ================= GIVEAWAY =================

class GiveawayView(discord.ui.View):
    def __init__(self, giveaway_id):
        super().__init__(timeout=None)
        self.giveaway_id = giveaway_id

    @discord.ui.button(label="🎉 Enter Giveaway (0)", style=discord.ButtonStyle.primary)
    async def enter(self, interaction: discord.Interaction, button: discord.ui.Button):

        data = load_giveaways()
        giveaway = data[self.giveaway_id]

        if interaction.user.id in giveaway["entries"]:
            await interaction.response.send_message("Already entered.", ephemeral=True)
            return

        giveaway["entries"].append(interaction.user.id)
        save_giveaways(data)

        button.label = f"🎉 Enter Giveaway ({len(giveaway['entries'])})"
        await interaction.message.edit(view=self)

        await interaction.response.send_message("Entered successfully.", ephemeral=True)

async def schedule_end(giveaway_id, delay):
    await asyncio.sleep(delay)
    await end_giveaway(giveaway_id)

async def end_giveaway(giveaway_id):
    data = load_giveaways()
    giveaway = data[giveaway_id]
    channel = bot.get_channel(giveaway["channel_id"])

    if not giveaway["entries"]:
        await channel.send("No entries.")
        return

    winner_id = random.choice(giveaway["entries"])
    winner = channel.guild.get_member(winner_id)

    giveaway["ended"] = True
    save_giveaways(data)

    embed = discord.Embed(
        title="🎉 GIVEAWAY ENDED",
        description=(
            f"🏆 Prize: **{giveaway['prize']}**\n"
            f"👥 Entries: {len(giveaway['entries'])}\n"
            f"🥇 Winner: {winner.mention}\n\n"
            f"🎫 Claim in <#{SUPPORT_CHANNEL_ID}>"
        ),
        color=discord.Color.purple()
    )

    await channel.send(embed=embed)

@bot.tree.command(name="giveaway", description="Start a giveaway")
async def giveaway(interaction: discord.Interaction, duration: int, prize: str):

    if not interaction.user.guild_permissions.manage_guild:
        await interaction.response.send_message("Need Manage Server permission.", ephemeral=True)
        return

    giveaway_id = str(interaction.id)

    embed = discord.Embed(
        title="✨ ARAB'S STUDIO GIVEAWAY ✨",
        description=f"🎁 Prize: **{prize}**\n⏰ Ends in {duration} minutes",
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
        "entries": [],
        "ended": False
    }
    save_giveaways(data)

    bot.loop.create_task(schedule_end(giveaway_id, duration * 60))

@bot.tree.command(name="reroll", description="Reroll giveaway")
async def reroll(interaction: discord.Interaction, message_id: str):

    if not interaction.user.guild_permissions.manage_guild:
        await interaction.response.send_message("Need Manage Server permission.", ephemeral=True)
        return

    data = load_giveaways()

    for giveaway in data.values():
        if str(giveaway["message_id"]) == message_id and giveaway["ended"]:
            winner_id = random.choice(giveaway["entries"])
            winner = interaction.guild.get_member(winner_id)
            await interaction.response.send_message(f"🔄 New Winner: {winner.mention}")
            return

    await interaction.response.send_message("Giveaway not found.", ephemeral=True)

# ================= CLEAN PREMIUM SERVER STATS =================

@bot.tree.command(name="serverstats", description="View server statistics")
async def serverstats(interaction: discord.Interaction):

    guild = interaction.guild
    data = load_giveaways()
    active = sum(1 for g in data.values() if not g.get("ended"))

    width, height = 1000, 550
    img = Image.new("RGBA", (width, height), (35, 0, 80))
    draw = ImageDraw.Draw(img)

    # soft panel
    panel = Image.new("RGBA", (800, 400), (255, 255, 255, 30))
    panel = panel.filter(ImageFilter.GaussianBlur(4))
    img.paste(panel, (100, 75), panel)

    if os.path.exists("as_logo.png"):
        logo = Image.open("as_logo.png").convert("RGBA")
        logo = logo.resize((600, 600))
        alpha = logo.split()[3]
        alpha = alpha.point(lambda p: p * 0.15)
        logo.putalpha(alpha)
        img.paste(logo, (200, -50), logo)

    font_title = ImageFont.truetype("Montserrat-Bold.ttf", 55)
    font_stat = ImageFont.truetype("Montserrat-Regular.ttf", 38)

    draw.text((160, 120), "ARAB'S STUDIO STATS", font=font_title, fill=(255, 255, 255))

    draw.text((180, 240), f"Members: {guild.member_count}", font=font_stat, fill=(255,255,255))
    draw.text((180, 300), f"Online: {sum(m.status != discord.Status.offline for m in guild.members)}", font=font_stat, fill=(255,255,255))
    draw.text((180, 360), f"Boost Level: {guild.premium_tier}", font=font_stat, fill=(255,255,255))
    draw.text((180, 420), f"Boost Count: {guild.premium_subscription_count}", font=font_stat, fill=(255,255,255))
    draw.text((180, 480), f"Active Giveaways: {active}", font=font_stat, fill=(255,255,255))

    path = f"stats_{guild.id}.png"
    img.save(path)

    await interaction.response.send_message(file=discord.File(path))

bot.run(TOKEN)
