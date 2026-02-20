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
import re

TOKEN = os.getenv("TOKEN")

WELCOME_CHANNEL_ID = 1472224372382109905
SUPPORT_CHANNEL_ID = 1472228682566340842
STAFF_LOG_CHANNEL_ID = 1473910880264519730
GIVEAWAY_FILE = "giveaways.json"

GW_COLOR = discord.Color(0x5E17EB)

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ================= READY =================

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Logged in as {bot.user}")

# ================= STORAGE =================

def load_giveaways():
    if not os.path.exists(GIVEAWAY_FILE):
        return {}
    with open(GIVEAWAY_FILE, "r") as f:
        return json.load(f)

def save_giveaways(data):
    with open(GIVEAWAY_FILE, "w") as f:
        json.dump(data, f, indent=4)

# ================= TIME =================

def parse_duration(duration: str):
    pattern = r"(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s)?"
    match = re.fullmatch(pattern, duration.lower())
    if not match:
        return None
    h = int(match.group(1)) if match.group(1) else 0
    m = int(match.group(2)) if match.group(2) else 0
    s = int(match.group(3)) if match.group(3) else 0
    return h*3600 + m*60 + s

def format_duration(seconds):
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    parts = []
    if h > 0: parts.append(f"{h}h")
    if m > 0: parts.append(f"{m}m")
    if s > 0: parts.append(f"{s}s")
    return " ".join(parts) if parts else "0s"

# ================= WELCOME SYSTEM =================

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

    spacing = 60
    typing_speed = 6
    cycle_lengths = [len(seq) * typing_speed for seq in sequences]
    total_cycle = sum(cycle_lengths)
    total_frames = total_cycle + 30

    for frame in range(total_frames):

        img = base_bg.copy()
        draw = ImageDraw.Draw(img)

        pattern_layer = Image.new("RGBA", (width * 2, height), (0, 0, 0, 0))
        p_draw = ImageDraw.Draw(pattern_layer)

        for y in range(0, height, spacing):
            for x in range(0, width * 2, spacing):
                p_draw.text((x, y), "X", font=font_small, fill=(255, 255, 255, 50))
                p_draw.text((x + 25, y + 25), "O", font=font_small, fill=(255, 255, 255, 50))

        offset = (frame * 4) % spacing
        cropped_pattern = pattern_layer.crop((offset, 0, offset + width, height))
        img = Image.alpha_composite(img, cropped_pattern)
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
            ], fill=(255, 255, 255, 245))

        stripe_offset = (frame * 6) % stripe_spacing
        cropped_stripes = stripe_canvas.crop(
            (stripe_spacing - stripe_offset, 0,
             stripe_spacing - stripe_offset + width, height)
        )

        img = Image.alpha_composite(img, cropped_stripes)
        draw = ImageDraw.Draw(img)

        letter_spacing = -8
        a_width = draw.textlength("A", font=font_logo)
        s_width = draw.textlength("S", font=font_logo)
        as_total_width = a_width + s_width + letter_spacing
        as_x = width - as_total_width - 140
        as_y = 40

        for glow in [45, 30, 15]:
            glow_layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
            glow_draw = ImageDraw.Draw(glow_layer)
            glow_draw.text((as_x, as_y - 12), "A", font=font_logo, fill=(255, 255, 255, 220))
            glow_draw.text((as_x + a_width + letter_spacing, as_y), "S", font=font_logo, fill=(255, 255, 255, 220))
            glow_layer = glow_layer.filter(ImageFilter.GaussianBlur(glow))
            img = Image.alpha_composite(img, glow_layer)

        draw = ImageDraw.Draw(img)
        draw.text((as_x, as_y - 12), "A", font=font_logo, fill=(255, 255, 255))
        draw.text((as_x + a_width + letter_spacing, as_y), "S", font=font_logo, fill=(255, 255, 255))

        draw.text((as_x - 100, as_y + 115),
                  "https://discord.gg/arabsstudio",
                  font=font_link,
                  fill=(255, 255, 255, 160))

        frames.append(img)

    gif_path = f"welcome_{member.id}.gif"
    frames[0].save(gif_path, save_all=True, append_images=frames[1:], duration=60, loop=0)
    return gif_path

@bot.event
async def on_member_join(member):
    channel = bot.get_channel(WELCOME_CHANNEL_ID)
    gif = await create_welcome_gif(member)
    await channel.send(
        content=f"{member.mention}, Welcome to Arab’s Studio — we’re glad to have you here!",
        file=discord.File(gif)
    )

# ================= SERVER INFO =================

@bot.tree.command(name="serverinfo", description="View server info")
async def serverinfo(interaction: discord.Interaction):
    guild = interaction.guild
    embed = discord.Embed(title=f"{guild.name} Info", color=GW_COLOR)
    embed.add_field(name="Members", value=guild.member_count)
    embed.add_field(name="Boost Level", value=guild.premium_tier)
    embed.add_field(name="Boost Count", value=guild.premium_subscription_count)
    embed.add_field(name="Created", value=guild.created_at.strftime("%Y-%m-%d"))
    await interaction.response.send_message(embed=embed)

# ================= GIVEAWAY SYSTEM =================

class GiveawayView(discord.ui.View):
    def __init__(self, giveaway_id):
        super().__init__(timeout=None)
        self.giveaway_id = giveaway_id

    @discord.ui.button(label="🎉 Enter Giveaway (0)", style=discord.ButtonStyle.primary)
    async def enter(self, interaction: discord.Interaction, button: discord.ui.Button):

        data = load_giveaways()
        giveaway = data[self.giveaway_id]

        if giveaway["ended"]:
            await interaction.response.send_message("This giveaway has ended.", ephemeral=True)
            return

        if interaction.user.id in giveaway["entries"]:
            await interaction.response.send_message("You already entered.", ephemeral=True)
            return

        giveaway["entries"].append(interaction.user.id)
        save_giveaways(data)

        button.label = f"🎉 Enter Giveaway ({len(giveaway['entries'])})"
        await interaction.message.edit(view=self)

        await interaction.response.send_message("You entered the giveaway!", ephemeral=True)

@bot.tree.command(name="giveaway", description="Start a giveaway")
async def giveaway(interaction: discord.Interaction,
                   duration: str,
                   winners: int,
                   prize: str,
                   requirements: str = "None"):

    if not interaction.user.guild_permissions.manage_guild:
        await interaction.response.send_message("You need Manage Server permission.", ephemeral=True)
        return

    duration_seconds = parse_duration(duration)
    if not duration_seconds:
        await interaction.response.send_message("Invalid duration format. Example: 1h30m, 5m, 30s", ephemeral=True)
        return

    giveaway_id = str(interaction.id)
    end_time = int(datetime.datetime.utcnow().timestamp()) + duration_seconds

    embed = discord.Embed(title="✨ ARAB'S STUDIO GIVEAWAY ✨", color=GW_COLOR)
    embed.add_field(name="🎁 Prize", value=f"**{prize}**", inline=False)
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
        "ended": False,
        "last_winners": []
    }
    save_giveaways(data)

    bot.loop.create_task(countdown_loop(giveaway_id))

async def countdown_loop(giveaway_id):
    while True:
        data = load_giveaways()
        giveaway = data[giveaway_id]

        if giveaway["ended"]:
            return

        remaining = giveaway["end_time"] - int(datetime.datetime.utcnow().timestamp())

        if remaining <= 0:
            await end_giveaway(giveaway_id)
            return

        channel = bot.get_channel(giveaway["channel_id"])
        message = await channel.fetch_message(giveaway["message_id"])

        embed = message.embeds[0]
        embed.set_field_at(3, name="⏳ Ends In", value=format_duration(remaining), inline=False)
        await message.edit(embed=embed)

        await asyncio.sleep(5)

async def end_giveaway(giveaway_id):
    data = load_giveaways()
    giveaway = data[giveaway_id]

    giveaway["ended"] = True

    channel = bot.get_channel(giveaway["channel_id"])
    message = await channel.fetch_message(giveaway["message_id"])

    entries = giveaway["entries"]

    winners = []
    if entries:
        winners = random.sample(entries, min(giveaway["winners"], len(entries)))

    giveaway["last_winners"] = winners
    save_giveaways(data)

    winner_mentions = "None"
    if winners:
        winner_mentions = " ".join(f"<@{w}>" for w in winners)

        for winner_id in winners:
            try:
                user = await bot.fetch_user(winner_id)
                embed = discord.Embed(title="🎉 YOU WON!", color=GW_COLOR)
                embed.add_field(name="🏆 Prize", value=f"**{giveaway['prize']}**", inline=False)
                embed.add_field(name="📩 Claim", value=f"Create a ticket in <#{SUPPORT_CHANNEL_ID}>", inline=False)
                await user.send(embed=embed)
            except:
                pass

    embed = discord.Embed(title="🎉 GIVEAWAY ENDED", color=GW_COLOR)
    embed.add_field(name="🎁 Prize", value=giveaway["prize"], inline=False)
    embed.add_field(name="👥 Entries", value=len(entries), inline=True)
    embed.add_field(name="🏆 Winner(s)", value=winner_mentions, inline=False)

    await message.edit(embed=embed, view=None)

    staff = bot.get_channel(STAFF_LOG_CHANNEL_ID)
    if staff:
        log = discord.Embed(title="🏆 Giveaway Ended", color=GW_COLOR)
        log.add_field(name="Prize", value=giveaway["prize"])
        log.add_field(name="Winners", value=winner_mentions)
        await staff.send(embed=log)

@bot.tree.command(name="reroll", description="Reroll a giveaway")
async def reroll(interaction: discord.Interaction, message_id: str):

    if not interaction.user.guild_permissions.manage_guild:
        await interaction.response.send_message(
            "You need Manage Server permission.",
            ephemeral=True
        )
        return

    data = load_giveaways()

    for gid, giveaway in data.items():
        if str(giveaway["message_id"]) == message_id and giveaway["ended"]:

            entries = giveaway["entries"]
            if not entries:
                await interaction.response.send_message(
                    "No entries to reroll.",
                    ephemeral=True
                )
                return

            old_winners = giveaway.get("last_winners", [])

            # Pick new winners
            new_winners = random.sample(
                entries,
                min(giveaway["winners"], len(entries))
            )

            giveaway["last_winners"] = new_winners
            save_giveaways(data)

            winner_mentions = " ".join(f"<@{w}>" for w in new_winners)

            # ================= DM OLD WINNERS =================
            for old in old_winners:
                if old not in new_winners:
                    try:
                        user = await bot.fetch_user(old)
                        embed = discord.Embed(
                            description="⚠️ You did not claim your reward in time. The giveaway has been rerolled.",
                            color=discord.Color.red()
                        )
                        await user.send(embed=embed)
                    except:
                        pass

            # ================= DM NEW WINNERS =================
            for winner_id in new_winners:
                try:
                    user = await bot.fetch_user(winner_id)
                    embed = discord.Embed(
                        title="🎉 YOU WON!",
                        color=GW_COLOR
                    )
                    embed.add_field(
                        name="🏆 Prize",
                        value=f"**{giveaway['prize']}**",
                        inline=False
                    )
                    embed.add_field(
                        name="📩 Claim",
                        value=f"Create a ticket in <#{SUPPORT_CHANNEL_ID}>",
                        inline=False
                    )
                    await user.send(embed=embed)
                except:
                    pass

            # ================= EDIT ORIGINAL MESSAGE =================
            channel = bot.get_channel(giveaway["channel_id"])
            message = await channel.fetch_message(giveaway["message_id"])

            embed = discord.Embed(
                title="🎉 GIVEAWAY ENDED",
                color=GW_COLOR
            )
            embed.add_field(name="🎁 Prize", value=giveaway["prize"], inline=False)
            embed.add_field(name="👥 Entries", value=len(entries), inline=True)
            embed.add_field(name="🏆 Winner(s)", value=winner_mentions, inline=False)
            embed.set_footer(text="🔄 This giveaway has been rerolled.")

            await message.edit(embed=embed)

            # ================= STAFF LOG =================
            staff = bot.get_channel(STAFF_LOG_CHANNEL_ID)
            if staff:
                log_embed = discord.Embed(
                    title="🔄 Giveaway Rerolled",
                    color=GW_COLOR
                )
                log_embed.add_field(name="🎁 Prize", value=giveaway["prize"], inline=False)
                log_embed.add_field(name="👥 New Winner(s)", value=winner_mentions, inline=False)
                log_embed.add_field(name="👮 Rerolled By", value=interaction.user.mention, inline=False)
                log_embed.add_field(name="🆔 Message ID", value=message_id, inline=False)
                await staff.send(embed=log_embed)

            await interaction.response.send_message(
                "Giveaway rerolled successfully.",
                ephemeral=True
            )
            return

    await interaction.response.send_message(
        "Giveaway not found.",
        ephemeral=True
    )

bot.run(TOKEN)