import discord
from discord.ext import commands
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import datetime
import aiohttp
import io
import os
import random

TOKEN = os.getenv("TOKEN")
WELCOME_CHANNEL_ID = 1472224372382109905

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)


@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Logged in as {bot.user}")


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


@bot.command()
async def testwelcome(ctx):
    gif = await create_welcome_gif(ctx.author)
    await ctx.send(
        content=f"{ctx.author.mention}, Welcome to Arab’s Studio — we’re glad to have you here!",
        file=discord.File(gif)
    )


# =========================
# GIVEAWAY SYSTEM
# =========================

class GiveawayView(discord.ui.View):
    def __init__(self, duration, prize):
        super().__init__(timeout=duration)
        self.entries = set()
        self.prize = prize
        self.message = None

    @discord.ui.button(label="🎉 Enter Giveaway", style=discord.ButtonStyle.primary)
    async def enter(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id in self.entries:
            await interaction.response.send_message("❌ You already entered!", ephemeral=True)
        else:
            self.entries.add(interaction.user.id)
            await interaction.response.send_message("✅ You entered the giveaway!", ephemeral=True)

    async def on_timeout(self):
        if not self.message:
            return

        channel = self.message.channel

        if len(self.entries) == 0:
            await channel.send("❌ Giveaway ended. No entries.")
            return

        winner_id = random.choice(list(self.entries))
        winner = channel.guild.get_member(winner_id)

        await channel.send(
            f"🎉 **GIVEAWAY ENDED!** 🎉\n"
            f"🏆 Prize: **{self.prize}**\n"
            f"🥇 Winner: {winner.mention}"
        )


@bot.tree.command(name="giveaway", description="Start a giveaway")
async def giveaway(interaction: discord.Interaction, duration: int, prize: str):

    if not interaction.user.guild_permissions.manage_guild:
        await interaction.response.send_message(
            "❌ You need Manage Server permission.",
            ephemeral=True
        )
        return

    duration_seconds = duration * 60
    end_time = datetime.datetime.utcnow() + datetime.timedelta(seconds=duration_seconds)

    embed = discord.Embed(
        title="🎉 GIVEAWAY 🎉",
        description=(
            f"🏆 Prize: **{prize}**\n\n"
            f"Click the button below to enter!\n\n"
            f"⏰ Ends: <t:{int(end_time.timestamp())}:R>"
        ),
        color=discord.Color.purple()
    )

    view = GiveawayView(duration_seconds, prize)
    await interaction.response.send_message(embed=embed, view=view)

    message = await interaction.original_response()
    view.message = message


bot.run(TOKEN)

