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
STAFF_LOG_CHANNEL_ID = 1473910880264519730  # 🔥 CHANGE THIS
SUPPORT_CHANNEL_ID = 1472228682566340842    # 🔥 CHANGE THIS
GIVEAWAY_FILE = "giveaways.json"

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# =========================
# GIVEAWAY STORAGE
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
# READY EVENT
# =========================

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Logged in as {bot.user}")

    data = load_giveaways()
    for giveaway_id, giveaway in data.items():
        remaining = giveaway["end_time"] - int(datetime.datetime.utcnow().timestamp())
        if remaining > 0:
            bot.loop.create_task(schedule_end(giveaway_id, remaining))

# =========================
# WELCOME SYSTEM (UNCHANGED)
# =========================

async def create_welcome_gif(member):
    width, height = 1000, 400
    frames = []

    font_title = ImageFont.truetype("Montserrat-Bold.ttf", 70)
    font_user = ImageFont.truetype("Montserrat-Regular.ttf", 40)
    font_small = ImageFont.truetype("Montserrat-Regular.ttf", 28)

    sequences = [
        ["W","WE","WEL","WELC","WELCO","WELCOM","WELCOME"],
        ["W","WI","WIL","WILL","WILLK","WILLKO","WILLKOM","WILLKOMM","WILLKOMME","WILLKOMMEN"],
        ["B","BE","BEN","BENV","BENVE","BENVEN","BENVENU","BENVENUT","BENVENUTO"],
    ]

    username = member.display_name
    member_count = f"Member #{member.guild.member_count}"
    join_time = datetime.datetime.now(datetime.timezone.utc).strftime("%H:%M UTC")

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

    typing_speed = 6
    cycle_lengths = [len(seq) * typing_speed for seq in sequences]
    total_cycle = sum(cycle_lengths)
    total_frames = total_cycle + 30

    for frame in range(total_frames):
        img = base_bg.copy()
        draw = ImageDraw.Draw(img)

        cycle_frame = frame % total_cycle
        cumulative = 0

        for seq, seq_length in zip(sequences, cycle_lengths):
            if cycle_frame < cumulative + seq_length:
                local_frame = cycle_frame - cumulative
                letter_index = min(len(seq)-1, local_frame // typing_speed)
                welcome_text = seq[letter_index]
                break
            cumulative += seq_length

        draw.text((60, 60), welcome_text, font=font_title, fill=(255, 255, 255))
        draw.text((200, 150), username, font=font_user, fill=(255, 255, 255))
        draw.text((200, 200), member_count, font=font_small, fill=(230, 230, 255))
        draw.text((200, 230), join_time, font=font_small, fill=(230, 230, 255))
        img.paste(avatar, (60, 150), avatar)

        frames.append(img)

    gif_path = f"welcome_{member.id}.gif"

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

@bot.event
async def on_member_join(member):
    channel = bot.get_channel(WELCOME_CHANNEL_ID)
    gif = await create_welcome_gif(member)
    await channel.send(
        content=f"{member.mention}, Welcome to Arab’s Studio — we’re glad to have you here!",
        file=discord.File(gif)
    )

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

        if self.giveaway_id not in data:
            await interaction.response.send_message("❌ Giveaway not found.", ephemeral=True)
            return

        if interaction.user.id in data[self.giveaway_id]["entries"]:
            await interaction.response.send_message("❌ You already entered!", ephemeral=True)
            return

        data[self.giveaway_id]["entries"].append(interaction.user.id)
        save_giveaways(data)

        count = len(data[self.giveaway_id]["entries"])
        button.label = f"🎉 Enter Giveaway ({count})"
        await interaction.message.edit(view=self)

        await interaction.response.send_message("✅ You entered!", ephemeral=True)

async def schedule_end(giveaway_id, delay):
    await asyncio.sleep(delay)
    await end_giveaway(giveaway_id)

async def end_giveaway(giveaway_id):
    data = load_giveaways()
    if giveaway_id not in data:
        return

    giveaway = data[giveaway_id]
    channel = bot.get_channel(giveaway["channel_id"])
    staff_channel = bot.get_channel(STAFF_LOG_CHANNEL_ID)

    entries = giveaway["entries"]
    winners_count = giveaway["winners"]

    if not entries:
        await channel.send("❌ Giveaway ended. No entries.")
    else:
        winners = random.sample(entries, min(winners_count, len(entries)))
        mentions = []

        for winner_id in winners:
            member = channel.guild.get_member(winner_id)
            if member:
                mentions.append(member.mention)

                try:
                    embed = discord.Embed(
                        title="🎉 YOU WON! 🎉",
                        description=(
                            f"🏆 **Prize:** {giveaway['prize']}\n"
                            f"🏠 **Server:** {channel.guild.name}\n\n"
                            f"🎫 To claim your reward, create a ticket in <#{SUPPORT_CHANNEL_ID}>"
                        ),
                        color=discord.Color.from_rgb(120, 0, 200)
                    )
                    await member.send(embed=embed)
                except:
                    pass

        embed = discord.Embed(
            title="🎉 GIVEAWAY ENDED! 🎉",
            description=(
                f"🏆 **Prize:** {giveaway['prize']}\n"
                f"👥 **Total Entries:** {len(entries)}\n"
                f"🥇 **Winner(s):** {', '.join(mentions)}\n\n"
                f"🎫 To claim your prize, create a ticket in <#{SUPPORT_CHANNEL_ID}>"
            ),
            color=discord.Color.from_rgb(120, 0, 200)
        )

        await channel.send(embed=embed)

        if staff_channel:
            await staff_channel.send(
                f"📢 Giveaway Ended\n"
                f"Prize: {giveaway['prize']}\n"
                f"Winners: {', '.join(mentions)}\n"
                f"Entries: {len(entries)}"
            )

    del data[giveaway_id]
    save_giveaways(data)

@bot.tree.command(name="giveaway", description="Start a giveaway")
async def giveaway(interaction: discord.Interaction, duration: int, winners: int, prize: str):

    if not interaction.user.guild_permissions.manage_guild:
        await interaction.response.send_message("❌ Need Manage Server permission.", ephemeral=True)
        return

    end_time = datetime.datetime.utcnow() + datetime.timedelta(minutes=duration)
    giveaway_id = str(int(end_time.timestamp())) + str(interaction.id)

    data = load_giveaways()
    data[giveaway_id] = {
        "channel_id": interaction.channel.id,
        "prize": prize,
        "winners": winners,
        "end_time": int(end_time.timestamp()),
        "entries": []
    }
    save_giveaways(data)

    embed = discord.Embed(
        title="✨ ARAB’S STUDIO GIVEAWAY ✨",
        description=(
            f"🎁 **Prize:** {prize}\n"
            f"👥 **Winners:** {winners}\n\n"
            f"⏰ Ends: <t:{int(end_time.timestamp())}:R>"
        ),
        color=discord.Color.from_rgb(120, 0, 200)
    )

    view = GiveawayView(giveaway_id)
    await interaction.response.send_message(embed=embed, view=view)

    bot.loop.create_task(schedule_end(giveaway_id, duration * 60))

@bot.tree.command(name="reroll", description="Reroll a giveaway")
async def reroll(interaction: discord.Interaction, message_id: str):

    if not interaction.user.guild_permissions.manage_guild:
        await interaction.response.send_message("❌ Need Manage Server permission.", ephemeral=True)
        return

    data = load_giveaways()

    for giveaway_id, giveaway in data.items():
        if str(giveaway.get("message_id", "")) == message_id:
            entries = giveaway["entries"]

            if not entries:
                await interaction.response.send_message("❌ No entries.", ephemeral=True)
                return

            winner_id = random.choice(entries)
            member = interaction.guild.get_member(winner_id)

            await interaction.response.send_message(
                f"🔄 New Winner: {member.mention}"
            )
            return

    await interaction.response.send_message("❌ Giveaway not found.", ephemeral=True)

bot.run(TOKEN)
