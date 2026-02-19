import discord
from discord.ext import commands
from PIL import Image, ImageDraw, ImageFont
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

GW_COLOR = discord.Color(0x5E17EB)

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

# ================= WELCOME =================

async def create_welcome_gif(member):
    width, height = 1000, 400
    frames = []

    font_title = ImageFont.truetype("Montserrat-Bold.ttf", 60)
    font_user = ImageFont.truetype("Montserrat-Regular.ttf", 35)
    font_small = ImageFont.truetype("Montserrat-Regular.ttf", 25)

    spacing = 60
    total_frames = 30

    async with aiohttp.ClientSession() as session:
        async with session.get(member.display_avatar.url) as resp:
            avatar_bytes = await resp.read()

    avatar = Image.open(io.BytesIO(avatar_bytes)).convert("RGBA")
    avatar = avatar.resize((120, 120))

    mask = Image.new("L", (120, 120), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, 120, 120), fill=255)
    avatar.putalpha(mask)

    for frame in range(total_frames):
        img = Image.new("RGBA", (width, height), (173, 216, 230))
        draw = ImageDraw.Draw(img)

        pattern = Image.new("RGBA", (width*2, height), (0,0,0,0))
        p_draw = ImageDraw.Draw(pattern)

        for y in range(0,height,spacing):
            for x in range(0,width*2,spacing):
                p_draw.text((x,y),"X",font=font_small,fill=(255,255,255,18))
                p_draw.text((x+30,y+30),"O",font=font_small,fill=(255,255,255,18))

        offset = (frame*4) % width
        cropped = pattern.crop((offset,0,offset+width,height))
        img = Image.alpha_composite(img,cropped)
        draw = ImageDraw.Draw(img)

        draw.text((80,80),"WELCOME TO ARAB'S STUDIO",font=font_title,fill=(255,255,255))
        draw.text((250,200),member.display_name,font=font_user,fill=(255,255,255))
        draw.text((250,250),f"Member #{member.guild.member_count}",font=font_small,fill=(200,200,200))

        img.paste(avatar,(80,200),avatar)
        frames.append(img)

    path=f"welcome_{member.id}.gif"
    frames[0].save(path,save_all=True,append_images=frames[1:],duration=70,loop=0)
    return path

@bot.event
async def on_member_join(member):
    channel = bot.get_channel(WELCOME_CHANNEL_ID)
    if channel:
        gif = await create_welcome_gif(member)
        await channel.send(content=f"{member.mention} welcome 💜", file=discord.File(gif))

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

            try:
                dm = discord.Embed(
                    title="🎉 YOU WON!",
                    description=f"🏆 Prize: **{giveaway['prize']}**\n🎫 Claim in <#{SUPPORT_CHANNEL_ID}>",
                    color=GW_COLOR
                )
                await member.send(embed=dm)
            except:
                pass

    embed = discord.Embed(
        title="🎉 GIVEAWAY ENDED",
        description=f"🎁 Prize: **{giveaway['prize']}**\n🥇 Winner(s): {', '.join(mentions)}",
        color=GW_COLOR
    )
    await channel.send(embed=embed)

    if staff_channel:
        jump_url = f"https://discord.com/channels/{channel.guild.id}/{channel.id}/{giveaway['message_id']}"

        staff_embed = discord.Embed(title="🏆 GIVEAWAY ENDED (STAFF)", color=GW_COLOR)
        staff_embed.add_field(name="Prize", value=giveaway["prize"], inline=False)
        staff_embed.add_field(name="Winners", value=", ".join(mentions), inline=False)
        staff_embed.add_field(name="Giveaway ID", value=giveaway_id, inline=False)

        view = discord.ui.View()
        view.add_item(discord.ui.Button(label="Jump to Giveaway", url=jump_url))

        await staff_channel.send(embed=staff_embed, view=view)

# ================= GIVEAWAY COMMAND =================

@bot.tree.command(name="giveaway", description="Start a giveaway")
async def giveaway(interaction: discord.Interaction, duration: int, winners: int, prize: str):

    if not interaction.user.guild_permissions.manage_guild:
        await interaction.response.send_message("Need Manage Server permission.", ephemeral=True)
        return

    giveaway_id = str(interaction.id)

    embed = discord.Embed(
        title="✨ ARAB'S STUDIO GIVEAWAY ✨",
        description=f"🎁 Prize: **{prize}**\n👥 Winners: {winners}\n⏰ Ends in {duration} minutes",
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

@bot.tree.command(name="reroll", description="Reroll a giveaway")
async def reroll(interaction: discord.Interaction, message_id: str):

    if not interaction.user.guild_permissions.manage_guild:
        await interaction.response.send_message("Need Manage Server permission.", ephemeral=True)
        return

    data = load_giveaways()
    staff_channel = bot.get_channel(STAFF_LOG_CHANNEL_ID)

    for giveaway_id, giveaway in data.items():
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

                    try:
                        dm = discord.Embed(
                            title="🎉 YOU WON (REROLL)!",
                            description=f"🏆 Prize: **{giveaway['prize']}**\n🎫 Claim in <#{SUPPORT_CHANNEL_ID}>",
                            color=GW_COLOR
                        )
                        await member.send(embed=dm)
                    except:
                        pass

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

            await interaction.response.send_message(f"🔄 New Winner(s): {', '.join(mentions)}")

            if staff_channel:
                staff_embed = discord.Embed(title="🔄 GIVEAWAY REROLLED (STAFF)", color=GW_COLOR)
                staff_embed.add_field(name="Prize", value=giveaway["prize"], inline=False)
                staff_embed.add_field(name="New Winners", value=", ".join(mentions), inline=False)
                staff_embed.add_field(name="Giveaway ID", value=giveaway_id, inline=False)
                staff_embed.add_field(name="Moderator", value=interaction.user.mention, inline=False)

                await staff_channel.send(embed=staff_embed)

            return

    await interaction.response.send_message("Giveaway not found.", ephemeral=True)

# ================= SERVER STATS WITH GLOW =================

@bot.tree.command(name="serverstats", description="Live server statistics")
async def serverstats(interaction: discord.Interaction):

    guild = interaction.guild
    data = load_giveaways()
    active = sum(1 for g in data.values() if not g.get("ended"))

    width, height = 1000, 500
    frames = []

    font_title = ImageFont.truetype("Montserrat-Bold.ttf", 50)
    font_stat = ImageFont.truetype("Montserrat-Regular.ttf", 30)

    total_frames = 50
    spacing = 80

    for frame in range(total_frames):

        img = Image.new("RGBA", (width, height), (30,30,30))
        draw = ImageDraw.Draw(img)

        pattern = Image.new("RGBA", (width*2,height),(0,0,0,0))
        p_draw = ImageDraw.Draw(pattern)

        for y in range(0,height,spacing):
            for x in range(0,width*2,spacing):
                p_draw.text((x,y),"X",font=font_stat,fill=(255,255,255,10))
                p_draw.text((x+35,y+35),"O",font=font_stat,fill=(255,255,255,10))

        offset=(frame*2)%width
        cropped=pattern.crop((offset,0,offset+width,height))
        img=Image.alpha_composite(img,cropped)
        draw=ImageDraw.Draw(img)

        draw.text((120,60),"ARAB'S STUDIO LIVE STATS",font=font_title,fill=(255,255,255))

        def glow_bar(x,y,value,max_value,label):
            bar_width=500
            percent=min(value/max_value,1)
            fill=int(bar_width*percent*(frame/total_frames))

            draw.rectangle((x-4,y-4,x+fill+4,y+29),fill=(70, 0, 150))      # outer glow
            draw.rectangle((x-2,y-2,x+fill+2,y+27),fill=(110, 0, 200))    # inner glow
            draw.rectangle((x,y,x+fill,y+25),fill=(160, 60, 255))         # main bar
            draw.text((x,y-30),f"{label}: {value}",font=font_stat,fill=(255,255,255))

        glow_bar(200,180,guild.member_count,500,"Members")
        glow_bar(200,250,sum(m.status!=discord.Status.offline for m in guild.members),200,"Online")
        glow_bar(200,320,guild.premium_subscription_count,50,"Boost Count")
        glow_bar(200,390,active,10,"Active Giveaways")

        frames.append(img)

    path=f"stats_{guild.id}.gif"
    frames[0].save(path,save_all=True,append_images=frames[1:],duration=80,loop=0)

    await interaction.response.send_message(file=discord.File(path))

bot.run(TOKEN)

