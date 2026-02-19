import discord
from discord.ext import commands
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import datetime
import aiohttp
import io
import os
import random
import json
import asyncio

TOKEN = os.getenv("TOKEN")

WELCOME_CHANNEL_ID = 1472224372382109905
SUPPORT_CHANNEL_ID = 1472228682566340842
STAFF_LOG_CHANNEL_ID = 1473910880264519730
GIVEAWAY_FILE = "giveaways.json"

intents = discord.Intents.all()
intents.members = True
intents.message_content = True

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

def format_duration(seconds):
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    parts = []
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    if secs > 0:
        parts.append(f"{secs}s")
    return " ".join(parts) if parts else "0s"

# ================= READY =================

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Logged in as {bot.user}")

# ================= WELCOME =================

async def create_welcome_gif(member):

    width, height = 1000, 400
    frames = []

    font_title = ImageFont.truetype("Montserrat-Bold.ttf", 70)
    font_user = ImageFont.truetype("Montserrat-Regular.ttf", 40)
    font_small = ImageFont.truetype("Montserrat-Regular.ttf", 28)

    base_bg = Image.new("RGB", (width, height))
    bg_draw = ImageDraw.Draw(base_bg)

    for y in range(height):
        for x in range(width):
            ratio = (x + y) / (width + height)
            r = int(55 - ratio * 30)
            g = 0
            b = int(105 - ratio * 50)
            bg_draw.point((x, y), fill=(r, g, b))

    base_bg = base_bg.convert("RGBA")

    async with aiohttp.ClientSession() as session:
        async with session.get(member.display_avatar.url) as resp:
            avatar_bytes = await resp.read()

    avatar = Image.open(io.BytesIO(avatar_bytes)).convert("RGBA")
    avatar = avatar.resize((110, 110))
    mask = Image.new("L", (110, 110), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, 110, 110), fill=255)
    avatar.putalpha(mask)

    img = base_bg.copy()
    draw = ImageDraw.Draw(img)

    draw.text((200,150), member.display_name, font=font_user, fill=(255,255,255))
    draw.text((200,200), f"Member #{member.guild.member_count}", font=font_small, fill=(230,230,255))

    img.paste(avatar, (60,150), avatar)

    gif_path = f"welcome_{member.id}.gif"
    img.save(gif_path)

    return gif_path

@bot.event
async def on_member_join(member):
    channel = bot.get_channel(WELCOME_CHANNEL_ID)
    gif = await create_welcome_gif(member)
    await channel.send(
        content=f"{member.mention}, Welcome to Arab’s Studio!",
        file=discord.File(gif)
    )

# ================= GIVEAWAY VIEW =================

class GiveawayView(discord.ui.View):
    def __init__(self, giveaway_id):
        super().__init__(timeout=None)
        self.giveaway_id = giveaway_id

    @discord.ui.button(label="🎉 Enter Giveaway (0)", style=discord.ButtonStyle.primary)
    async def enter(self, interaction: discord.Interaction, button: discord.ui.Button):

        data = load_giveaways()

        if self.giveaway_id not in data:
            await interaction.response.send_message("Expired.", ephemeral=True)
            return

        giveaway = data[self.giveaway_id]

        if giveaway["ended"]:
            await interaction.response.send_message("Ended.", ephemeral=True)
            return

        if interaction.user.id in giveaway["entries"]:
            await interaction.response.send_message("Already entered.", ephemeral=True)
            return

        giveaway["entries"].append(interaction.user.id)
        save_giveaways(data)

        button.label = f"🎉 Enter Giveaway ({len(giveaway['entries'])})"
        await interaction.message.edit(view=self)

        await interaction.response.send_message("Entered!", ephemeral=True)

# ================= GIVEAWAY COMMAND =================

@bot.tree.command(name="giveaway", description="Start a giveaway")
async def giveaway(interaction: discord.Interaction,
                   duration_seconds: int,
                   winners: int,
                   prize: str,
                   requirements: str = "None"):

    if not interaction.user.guild_permissions.manage_guild:
        await interaction.response.send_message("Need Manage Server permission.", ephemeral=True)
        return

    giveaway_id = str(interaction.id)
    end_time = int(datetime.datetime.utcnow().timestamp()) + duration_seconds

    embed = discord.Embed(
        title="🎉 ARAB'S STUDIO GIVEAWAY 🎉",
        color=discord.Color.purple()
    )

    embed.add_field(name="🎁 Prize", value=prize, inline=False)
    embed.add_field(name="👥 Winners", value=str(winners), inline=True)
    embed.add_field(name="📌 Requirements", value=requirements, inline=True)
    embed.add_field(name="⏳ Ends In", value=format_duration(duration_seconds), inline=False)

    view = GiveawayView(giveaway_id)

    await interaction.response.send_message(embed=embed, view=view)
    message = await interaction.original_response()

    data = load_giveaways()
    data[giveaway_id] = {
        "message_id": message.id,
        "channel_id": interaction.channel.id,
        "end_time": end_time,
        "winners": winners,
        "prize": prize,
        "requirements": requirements,
        "entries": [],
        "ended": False
    }
    save_giveaways(data)

    bot.loop.create_task(countdown_loop(giveaway_id))

# ================= COUNTDOWN =================

async def countdown_loop(giveaway_id):

    while True:
        data = load_giveaways()
        if giveaway_id not in data:
            return

        giveaway = data[giveaway_id]
        if giveaway["ended"]:
            return

        remaining = giveaway["end_time"] - int(datetime.datetime.utcnow().timestamp())

        if remaining <= 0:
            await end_giveaway(giveaway_id)
            return

        channel = bot.get_channel(giveaway["channel_id"])
        if not channel:
            return

        try:
            message = await channel.fetch_message(giveaway["message_id"])
        except:
            return

        embed = message.embeds[0]
        embed.set_field_at(3, name="⏳ Ends In", value=format_duration(remaining), inline=False)
        await message.edit(embed=embed)

        await asyncio.sleep(5)

# ================= END GIVEAWAY =================

async def end_giveaway(giveaway_id):

    data = load_giveaways()
    giveaway = data[giveaway_id]

    channel = bot.get_channel(giveaway["channel_id"])
    staff_channel = bot.get_channel(STAFF_LOG_CHANNEL_ID)

    winners = random.sample(
        giveaway["entries"],
        min(giveaway["winners"], len(giveaway["entries"]))
    )

    giveaway["ended"] = True
    giveaway["last_winners"] = winners
    save_giveaways(data)

    mentions = []

    for w in winners:
        member = channel.guild.get_member(w)
        if member:
            mentions.append(member.mention)
            try:
                await member.send(
                    f"🎉 You won **{giveaway['prize']}**!\nClaim in <#{SUPPORT_CHANNEL_ID}>"
                )
            except:
                pass

    embed = discord.Embed(
        title="🏆 GIVEAWAY ENDED",
        description=f"🎁 {giveaway['prize']}\n🥇 Winner(s): {', '.join(mentions)}",
        color=discord.Color.purple()
    )

    await channel.send(embed=embed)

    if staff_channel:
        await staff_channel.send(embed=embed)

# ================= REROLL =================

@bot.tree.command(name="reroll", description="Reroll a giveaway")
async def reroll(interaction: discord.Interaction, message_id: str):

    if not interaction.user.guild_permissions.manage_guild:
        await interaction.response.send_message("Need Manage Server permission.", ephemeral=True)
        return

    data = load_giveaways()

    for giveaway_id, giveaway in data.items():
        if str(giveaway["message_id"]) == message_id and giveaway["ended"]:

            winners = random.sample(
                giveaway["entries"],
                min(giveaway["winners"], len(giveaway["entries"]))
            )

            giveaway["last_winners"] = winners
            save_giveaways(data)

            mentions = []

            for w in winners:
                member = interaction.guild.get_member(w)
                if member:
                    mentions.append(member.mention)

            await interaction.response.send_message(
                f"🔄 New Winner(s): {', '.join(mentions)}"
            )
            return

    await interaction.response.send_message("Giveaway not found.", ephemeral=True)

# ================= SERVERINFO =================

@bot.tree.command(name="serverinfo", description="View server information")
async def serverinfo(interaction: discord.Interaction):

    guild = interaction.guild

    embed = discord.Embed(
        title=f"{guild.name} Server Info",
        color=discord.Color.purple()
    )

    embed.add_field(name="Members", value=guild.member_count)
    embed.add_field(name="Boost Level", value=guild.premium_tier)
    embed.add_field(name="Boost Count", value=guild.premium_subscription_count)
    embed.add_field(name="Created", value=guild.created_at.strftime("%Y-%m-%d"))

    await interaction.response.send_message(embed=embed)

bot.run(TOKEN)

