import discord
from discord.ext import commands
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import aiohttp
import asyncio
import datetime
import io
import os
import random
import re
import sqlite3

print("MAIN SCRIPT STARTING")

TOKEN = os.getenv("TOKEN")
if not TOKEN:
    raise RuntimeError("TOKEN not found in Railway variables")

WELCOME_CHANNEL_ID = 1472224372382109905
BOOSTER_ROLE_ID = 1472274201686839450
VIP_ROLE_ID = 1473695955869110324

intents = discord.Intents.default()
intents.members = True
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# ================= DATABASE =================

conn = sqlite3.connect("giveaways.db")
c = conn.cursor()

c.execute("""
CREATE TABLE IF NOT EXISTS giveaways (
    id TEXT PRIMARY KEY,
    message_id INTEGER,
    channel_id INTEGER,
    end_time INTEGER,
    winners INTEGER,
    prize TEXT,
    required_role INTEGER,
    theme TEXT,
    ended INTEGER
)
""")

c.execute("""
CREATE TABLE IF NOT EXISTS entries (
    giveaway_id TEXT,
    user_id INTEGER
)
""")

conn.commit()

# ================= THEMES =================

THEMES = {
    "neon": {
        "top": (40, 0, 80),
        "bottom": (120, 0, 255),
        "shine": (0, 255, 255, 90),
        "stripe": (0, 255, 255, 200),
        "logo": (255, 255, 255)
    },
    "dark": {
        "top": (30, 0, 60),
        "bottom": (70, 0, 120),
        "shine": (255, 255, 255, 60),
        "stripe": (255, 255, 255, 180),
        "logo": (255, 255, 255)
    },
    "gold": {
        "top": (20, 15, 0),
        "bottom": (120, 90, 0),
        "shine": (255, 215, 0, 120),
        "stripe": (255, 215, 0, 220),
        "logo": (255, 215, 0)
    }
}

# ================= READY =================

@bot.event
async def on_ready():
    print("BOT ONLINE:", bot.user)
    await bot.tree.sync()
    await recover_giveaways()

# ================= UTILS =================

def parse_duration(duration):
    pattern = r"(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s)?"
    match = re.fullmatch(pattern, duration.lower())
    if not match:
        return None
    h = int(match.group(1)) if match.group(1) else 0
    m = int(match.group(2)) if match.group(2) else 0
    s = int(match.group(3)) if match.group(3) else 0
    return h*3600 + m*60 + s

def generate_background(width, height, theme):
    colors = THEMES[theme]
    img = Image.new("RGB", (width, height))
    draw = ImageDraw.Draw(img)
    for y in range(height):
        ratio = y / height
        r = int(colors["top"][0]*(1-ratio)+colors["bottom"][0]*ratio)
        g = int(colors["top"][1]*(1-ratio)+colors["bottom"][1]*ratio)
        b = int(colors["top"][2]*(1-ratio)+colors["bottom"][2]*ratio)
        for x in range(width):
            draw.point((x,y), fill=(r,g,b))
    return img.convert("RGBA")

# ================= GIVEAWAY GIF =================

async def create_giveaway_gif(prize, theme):
    width, height = 800, 300
    frames = []
    colors = THEMES[theme]

    font_big = ImageFont.truetype("Montserrat-Bold.ttf", 70)
    font_prize = ImageFont.truetype("Montserrat-Regular.ttf", 40)
    font_small = ImageFont.truetype("Montserrat-Regular.ttf", 28)
    font_logo = ImageFont.truetype("Montserrat-Bold.ttf", 80)

    sequence = ["G","GI","GIV","GIVE","GIVEA","GIVEAW","GIVEAWA","GIVEAWAY"]

    base = generate_background(width, height, theme)
    spacing = 60
    total_frames = len(sequence)*5 + 20

    for frame in range(total_frames):
        img = base.copy()

        # moving XO
        layer = Image.new("RGBA", (width*2, height), (0,0,0,0))
        p = ImageDraw.Draw(layer)
        for y in range(0,height,spacing):
            for x in range(0,width*2,spacing):
                p.text((x,y),"X",font=font_small,fill=(255,255,255,50))
                p.text((x+25,y+25),"O",font=font_small,fill=(255,255,255,50))
        offset = (frame*4)%spacing
        crop = layer.crop((offset,0,offset+width,height))
        img = Image.alpha_composite(img,crop)

        draw = ImageDraw.Draw(img)

        text = sequence[min(len(sequence)-1,frame//5)]
        tw = draw.textlength(text,font=font_big)
        tx = (width-tw)/2
        ty = 40
        draw.text((tx,ty),text,font=font_big,fill=(255,255,255))

        # shine
        shine = Image.new("RGBA",img.size,(0,0,0,0))
        sdraw = ImageDraw.Draw(shine)
        sx = (frame*20)%(width+200)-200
        sdraw.rectangle([sx,ty-10,sx+80,ty+80],fill=colors["shine"])
        img = Image.alpha_composite(img,shine)

        draw = ImageDraw.Draw(img)

        pw = draw.textlength(prize,font=font_prize)
        draw.text(((width-pw)/2,130),prize,font=font_prize,fill=(230,230,255))

        # glow logo
        for blur in [15,8,4]:
            glow = Image.new("RGBA",img.size,(0,0,0,0))
            g = ImageDraw.Draw(glow)
            g.text((width-120,10),"AS",font=font_logo,
                   fill=(*colors["logo"],200))
            glow = glow.filter(ImageFilter.GaussianBlur(blur))
            img = Image.alpha_composite(img,glow)

        draw = ImageDraw.Draw(img)
        draw.text((width-120,10),"AS",font=font_logo,
                  fill=colors["logo"])

        # bottom stripe
        stripe = Image.new("RGBA",(width*2,height),(0,0,0,0))
        sd = ImageDraw.Draw(stripe)
        for i in range(0,width*2,150):
            sd.polygon([
                (i,height-40),
                (i+60,height-40),
                (i+40,height),
                (i-20,height)
            ],fill=colors["stripe"])
        so = (frame*6)%150
        img = Image.alpha_composite(img,
              stripe.crop((150-so,0,150-so+width,height)))

        frames.append(img.convert("RGB"))

    path=f"gw_{random.randint(1,999999)}.gif"
    frames[0].save(path,save_all=True,
                   append_images=frames[1:],
                   duration=60,loop=0)
    return path

# ================= GIVEAWAY VIEW =================

class GiveawayView(discord.ui.View):
    def __init__(self,gid):
        super().__init__(timeout=None)
        self.gid=gid

    @discord.ui.button(label="🎉 Enter",style=discord.ButtonStyle.primary)
    async def enter(self,interaction:discord.Interaction,button:discord.ui.Button):

        c.execute("SELECT required_role, ended FROM giveaways WHERE id=?",(self.gid,))
        required_role,ended=c.fetchone()

        if ended:
            await interaction.response.send_message("Ended.",ephemeral=True)
            return

        if required_role and required_role not in [r.id for r in interaction.user.roles]:
            await interaction.response.send_message("Missing role.",ephemeral=True)
            return

        c.execute("SELECT 1 FROM entries WHERE giveaway_id=? AND user_id=?",
                  (self.gid,interaction.user.id))
        if c.fetchone():
            await interaction.response.send_message("Already entered.",ephemeral=True)
            return

        entries=1
        if BOOSTER_ROLE_ID in [r.id for r in interaction.user.roles]:
            entries+=5
        if VIP_ROLE_ID in [r.id for r in interaction.user.roles]:
            entries+=2

        for _ in range(entries):
            c.execute("INSERT INTO entries VALUES (?,?)",(self.gid,interaction.user.id))
        conn.commit()

        c.execute("SELECT COUNT(*) FROM entries WHERE giveaway_id=?",(self.gid,))
        total=c.fetchone()[0]

        embed=interaction.message.embeds[0]
        for i,field in enumerate(embed.fields):
            if field.name=="🎟 Entries":
                embed.set_field_at(i,name="🎟 Entries",
                                   value=str(total),inline=True)
                break

        await interaction.message.edit(embed=embed,view=self)
        await interaction.response.send_message(
            f"Entered with {entries} entries!",ephemeral=True)

# ================= GIVEAWAY COMMAND =================

@bot.tree.command(name="giveaway")
async def giveaway(interaction:discord.Interaction,
                   duration:str,
                   winners:int,
                   prize:str,
                   theme:str="dark",
                   required_role:discord.Role=None):

    if theme not in THEMES:
        await interaction.response.send_message(
            "Theme must be neon, dark, or gold",
            ephemeral=True)
        return

    seconds=parse_duration(duration)
    if not seconds:
        await interaction.response.send_message("Invalid duration.",ephemeral=True)
        return

    await interaction.response.defer()

    end_time=int(datetime.datetime.utcnow().timestamp())+seconds
    gid=str(interaction.id)

    gif=await create_giveaway_gif(prize,theme)
    file=discord.File(gif)

    embed=discord.Embed(title="🎉 GIVEAWAY 🎉")
    embed.set_image(url=f"attachment://{os.path.basename(gif)}")
    embed.add_field(name="🎁 Prize",value=prize,inline=False)
    embed.add_field(name="👥 Winners",value=str(winners))
    embed.add_field(name="⏳ Ends",value=f"<t:{end_time}:R>")
    embed.add_field(name="🎟 Entries",value="0",inline=True)

    if required_role:
        embed.add_field(name="📌 Required Role",
                        value=required_role.mention,
                        inline=False)

    view=GiveawayView(gid)

    await interaction.followup.send(embed=embed,view=view,file=file)
    msg=await interaction.original_response()

    c.execute("INSERT INTO giveaways VALUES (?,?,?,?,?,?,?,?,?)",
              (gid,msg.id,interaction.channel.id,
               end_time,winners,prize,
               required_role.id if required_role else None,
               theme,0))
    conn.commit()

    bot.loop.create_task(countdown(gid))

# ================= END =================

async def countdown(gid):
    while True:
        c.execute("SELECT end_time, ended FROM giveaways WHERE id=?",(gid,))
        end_time,ended=c.fetchone()
        if ended: return
        if end_time-int(datetime.datetime.utcnow().timestamp())<=0:
            await end_giveaway(gid)
            return
        await asyncio.sleep(5)

async def end_giveaway(gid):
    c.execute("SELECT channel_id,message_id,winners,prize FROM giveaways WHERE id=?",(gid,))
    channel_id,message_id,winner_count,prize=c.fetchone()

    c.execute("UPDATE giveaways SET ended=1 WHERE id=?",(gid,))
    conn.commit()

    c.execute("SELECT user_id FROM entries WHERE giveaway_id=?",(gid,))
    entries=[r[0] for r in c.fetchall()]
    winners=random.sample(entries,min(winner_count,len(entries))) if entries else []

    channel=bot.get_channel(channel_id)
    message=await channel.fetch_message(message_id)

    await message.edit(content="🎊 Drawing winners...",embed=None)
    await asyncio.sleep(2)

    embed=discord.Embed(title="🎉 GIVEAWAY ENDED 🎉",
                        description="🌟 Congratulations! 🌟",
                        color=discord.Color.gold())
    embed.add_field(name="🎁 Prize",value=prize,inline=False)
    embed.add_field(name="🏆 Winners",
                    value=" 🌟 ".join(f"<@{w}>" for w in winners)
                    if winners else "None",
                    inline=False)

    await message.edit(content=None,embed=embed,view=None)

async def recover_giveaways():
    c.execute("SELECT id FROM giveaways WHERE ended=0")
    for (gid,) in c.fetchall():
        bot.loop.create_task(countdown(gid))

bot.run(TOKEN)
