import discord
from discord.ext import commands
from PIL import Image, ImageDraw, ImageFont
import datetime
import os
import random
import json
import asyncio

TOKEN = os.getenv("TOKEN")

SUPPORT_CHANNEL_ID = 1472228682566340842
STAFF_LOG_CHANNEL_ID = 1473910880264519730
GIVEAWAY_FILE = "giveaways.json"

GW_COLOR = discord.Color(0x5E17EB)  # 🔥 Premium Purple

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
    print("✅ Slash commands synced.")
    print(f"Logged in as {bot.user}")

# ================= GIVEAWAY =================

class GiveawayView(discord.ui.View):
    def __init__(self, giveaway_id):
        super().__init__(timeout=None)
        self.giveaway_id = giveaway_id

    @discord.ui.button(label="🎉 Enter Giveaway (0)", style=discord.ButtonStyle.secondary)
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
    staff_channel = bot.get_channel(STAFF_LOG_CHANNEL_ID)

    if not giveaway["entries"]:
        await channel.send("No entries.")
        return

    winners = random.sample(
        giveaway["entries"],
        min(giveaway["winners"], len(giveaway["entries"]))
    )

    giveaway["ended"] = True
    giveaway["last_winners"] = winners
    save_giveaways(data)

    mentions = []

    for winner_id in winners:
        member = channel.guild.get_member(winner_id)
        if member:
            mentions.append(member.mention)

            # 🔥 Winner DM
            try:
                embed = discord.Embed(
                    title="🎉 YOU WON THE GIVEAWAY! 🎉",
                    description=(
                        f"🏆 Prize: **{giveaway['prize']}**\n\n"
                        f"🎫 Create a ticket in <#{SUPPORT_CHANNEL_ID}> to claim."
                    ),
                    color=GW_COLOR
                )
                await member.send(embed=embed)
            except:
                pass

    # Public message
    embed = discord.Embed(
        title="🎉 GIVEAWAY ENDED",
        description=(
            f"🏆 Prize: **{giveaway['prize']}**\n"
            f"👥 Entries: {len(giveaway['entries'])}\n"
            f"🥇 Winner(s): {', '.join(mentions)}\n\n"
            f"🎫 Claim in <#{SUPPORT_CHANNEL_ID}>"
        ),
        color=GW_COLOR
    )

    await channel.send(embed=embed)

    # 🔥 Staff Log
    if staff_channel:
        await staff_channel.send(
            f"🏆 Giveaway Ended\nPrize: {giveaway['prize']}\nWinners: {', '.join(mentions)}"
        )

@bot.tree.command(name="giveaway", description="Start a giveaway")
async def giveaway(interaction: discord.Interaction, duration: int, winners: int, prize: str):

    if not interaction.user.guild_permissions.manage_guild:
        await interaction.response.send_message("Need Manage Server permission.", ephemeral=True)
        return

    giveaway_id = str(interaction.id)

    embed = discord.Embed(
        title="✨ ARAB'S STUDIO GIVEAWAY ✨",
        description=(
            f"🎁 Prize: **{prize}**\n"
            f"👥 Winners: {winners}\n"
            f"⏰ Ends in {duration} minutes"
        ),
        color=GW_COLOR
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
        "winners": winners,
        "ended": False
    }
    save_giveaways(data)

    bot.loop.create_task(schedule_end(giveaway_id, duration * 60))

# ================= REROLL =================

@bot.tree.command(name="reroll", description="Reroll giveaway")
async def reroll(interaction: discord.Interaction, message_id: str):

    if not interaction.user.guild_permissions.manage_guild:
        await interaction.response.send_message("Need Manage Server permission.", ephemeral=True)
        return

    data = load_giveaways()
    staff_channel = bot.get_channel(STAFF_LOG_CHANNEL_ID)

    for giveaway in data.values():
        if str(giveaway["message_id"]) == message_id and giveaway["ended"]:

            old_winners = giveaway.get("last_winners", [])

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

                    # New Winner DM
                    try:
                        embed = discord.Embed(
                            title="🎉 YOU WON (REROLL)! 🎉",
                            description=(
                                f"🏆 Prize: **{giveaway['prize']}**\n\n"
                                f"🎫 Create a ticket in <#{SUPPORT_CHANNEL_ID}> to claim."
                            ),
                            color=GW_COLOR
                        )
                        await member.send(embed=embed)
                    except:
                        pass

            # Old Winner DM
            for old in old_winners:
                if old not in winners:
                    old_member = interaction.guild.get_member(old)
                    if old_member:
                        try:
                            await old_member.send(
                                "⚠️ You did not claim your reward in time. The giveaway has been rerolled."
                            )
                        except:
                            pass

            await interaction.response.send_message(
                f"🔄 New Winner(s): {', '.join(mentions)}"
            )

            # 🔥 Staff Log
            if staff_channel:
                await staff_channel.send(
                    f"🔄 Giveaway Rerolled\nPrize: {giveaway['prize']}\nNew Winners: {', '.join(mentions)}"
                )

            return

    await interaction.response.send_message("Giveaway not found.", ephemeral=True)

# ================= INFINITE SMOOTH SERVER STATS =================

@bot.tree.command(name="serverstats", description="Live server statistics")
async def serverstats(interaction: discord.Interaction):

    guild = interaction.guild
    data = load_giveaways()
    active = sum(1 for g in data.values() if not g.get("ended"))

    width, height = 1000, 500
    frames = []

    font_title = ImageFont.truetype("Montserrat-Bold.ttf", 50)
    font_stat = ImageFont.truetype("Montserrat-Regular.ttf", 30)

    spacing = 80
    total_frames = 50

    for frame in range(total_frames):

        img = Image.new("RGBA", (width, height), (30, 30, 30))
        draw = ImageDraw.Draw(img)

        # Continuous XO scroll
        pattern = Image.new("RGBA", (width * 2, height), (0,0,0,0))
        p_draw = ImageDraw.Draw(pattern)

        for y in range(0, height, spacing):
            for x in range(0, width * 2, spacing):
                p_draw.text((x, y), "X", font=font_stat, fill=(255,255,255,15))
                p_draw.text((x+35, y+35), "O", font=font_stat, fill=(255,255,255,15))

        offset = (frame * 3) % width
        cropped = pattern.crop((offset, 0, offset + width, height))
        img = Image.alpha_composite(img, cropped)
        draw = ImageDraw.Draw(img)

        draw.text((120, 60), "ARAB'S STUDIO LIVE STATS", font=font_title, fill=(255,255,255))

        draw.text((200, 180), f"Members: {guild.member_count}", font=font_stat, fill=(255,255,255))
        draw.text((200, 230), f"Online: {sum(m.status != discord.Status.offline for m in guild.members)}", font=font_stat, fill=(255,255,255))
        draw.text((200, 280), f"Boost Level: {guild.premium_tier}", font=font_stat, fill=(255,255,255))
        draw.text((200, 330), f"Boost Count: {guild.premium_subscription_count}", font=font_stat, fill=(255,255,255))
        draw.text((200, 380), f"Active Giveaways: {active}", font=font_stat, fill=(255,255,255))

        frames.append(img)

    path = f"stats_{guild.id}.gif"
    frames[0].save(
        path,
        save_all=True,
        append_images=frames[1:],
        duration=80,
        loop=0,   # infinite
        disposal=2
    )

    await interaction.response.send_message(file=discord.File(path))

bot.run(TOKEN)
