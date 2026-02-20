import discord
from discord.ext import commands
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import datetime
import aiohttp
import io
import os
import arabic_reshaper
from bidi.algorithm import get_display

WELCOME_CHANNEL_ID = 1472224372382109905


class Welcome(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    async def create_welcome_gif(self, member):

        width, height = 1000, 400
        frames = []

        # Fonts
        font_title = ImageFont.truetype("Montserrat-Bold.ttf", 70)
        font_user = ImageFont.truetype("Montserrat-Regular.ttf", 40)
        font_small = ImageFont.truetype("Montserrat-Regular.ttf", 28)
        font_logo = ImageFont.truetype("Montserrat-Bold.ttf", 110)
        font_link = ImageFont.truetype("Montserrat-Regular.ttf", 24)

        # Arabic font
        font_arabic = ImageFont.truetype("NotoSans-Bold.ttf", 70)

        # ================= SEQUENCES =================

        sequences = [
            ["W","WE","WEL","WELC","WELCO","WELCOM","WELCOME"],
            ["W","WI","WIL","WILL","WILLK","WILLKO","WILLKOM","WILLKOMM","WILLKOMME","WILLKOMMEN"],
            ["B","BE","BEN","BENV","BENVE","BENVEN","BENVENU","BENVENUT","BENVENUTO"],
        ]

        # Arabic typing sequence
        arabic_full = "مرحباً بك"
        arabic_sequence = []

        for i in range(1, len(arabic_full) + 1):
            partial = arabic_full[:i]
            reshaped = arabic_reshaper.reshape(partial)
            bidi_text = get_display(reshaped)
            arabic_sequence.append(bidi_text)

        sequences.append(arabic_sequence)

        username = member.display_name
        member_count = f"Member #{member.guild.member_count}"
        join_time = datetime.datetime.now(datetime.timezone.utc).strftime("%H:%M UTC")

        # ===== Gradient Background =====
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

        # ===== Fetch Avatar =====
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

            # ===== Typing Animation =====
            cycle_frame = frame % total_cycle
            cumulative = 0
            welcome_text = "WELCOME"

            for seq, seq_length in zip(sequences, cycle_lengths):
                if cycle_frame < cumulative + seq_length:
                    local_frame = cycle_frame - cumulative
                    letter_index = min(len(seq)-1, local_frame // typing_speed)
                    welcome_text = seq[letter_index]
                    break
                cumulative += seq_length

            # ===== Draw Welcome Text (Arabic aligned right) =====
            if welcome_text in arabic_sequence:
                text_width = draw.textlength(welcome_text, font=font_arabic)
                draw.text(
                    (width - text_width - 60, 60),
                    welcome_text,
                    font=font_arabic,
                    fill=(255, 255, 255)
                )
            else:
                draw.text(
                    (60, 60),
                    welcome_text,
                    font=font_title,
                    fill=(255, 255, 255)
                )

            # ===== Other Text =====
            draw.text((200, 150), username, font=font_user, fill=(255, 255, 255))
            draw.text((200, 200), member_count, font=font_small, fill=(230, 230, 255))
            draw.text((200, 230), join_time, font=font_small, fill=(230, 230, 255))

            img.paste(avatar, (60, 150), avatar)

            frames.append(img)

        gif_path = f"welcome_{member.id}.gif"
        frames[0].save(gif_path, save_all=True, append_images=frames[1:], duration=60, loop=0)

        return gif_path

    # ================= MEMBER JOIN =================

    @commands.Cog.listener()
    async def on_member_join(self, member):

        channel = self.bot.get_channel(WELCOME_CHANNEL_ID)
        if not channel:
            return

        gif_path = await self.create_welcome_gif(member)

        await channel.send(
            content=f"{member.mention}, Welcome to Arab’s Studio — we’re glad to have you here!",
            file=discord.File(gif_path)
        )

        try:
            os.remove(gif_path)
        except:
            pass


async def setup(bot):
    await bot.add_cog(Welcome(bot))