import discord
from discord.ext import commands
from PIL import Image, ImageDraw, ImageFont
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

        width, height = 900, 350
        frames = []

        # ================= FONTS =================
        font_title = ImageFont.truetype("NotoSans-Bold.ttf", 70)
        font_user = ImageFont.truetype("NotoSans-Regular.ttf", 40)
        font_small = ImageFont.truetype("NotoSans-Regular.ttf", 28)
        font_logo = ImageFont.truetype("NotoSans-Bold.ttf", 110)
        font_link = ImageFont.truetype("NotoSans-Regular.ttf", 24)

        font_arabic = ImageFont.truetype("NotoSansArabic_Condensed-Bold.ttf", 70)
        font_jp = ImageFont.truetype("NotoSansJP-Bold.ttf", 70)

        # ================= WORDS =================
        words = [
            "WELCOME",
            "WILLKOMMEN",
            "BIENVENUE",
            "HOŞ GELDİN",
            "BENVENUTO",
            "ようこそ"
        ]

        arabic_full = "مرحباً بك"
        reshaped = arabic_reshaper.reshape(arabic_full)
        arabic_word = get_display(reshaped)
        words.append(arabic_word)

        username = member.display_name
        member_count = f"Member #{member.guild.member_count}"
        join_time = datetime.datetime.now(datetime.timezone.utc).strftime("%H:%M UTC")

        # ================= BACKGROUND =================
        base_bg = Image.new("RGBA", (width, height), (40, 0, 80))

        # ================= PREBUILD PATTERN =================
        spacing = 60
        pattern_layer = Image.new("RGBA", (width * 2, height), (0, 0, 0, 0))
        p_draw = ImageDraw.Draw(pattern_layer)

        for y in range(0, height, spacing):
            for x in range(0, width * 2, spacing):
                p_draw.text((x, y), "X", font=font_small, fill=(255, 255, 255, 50))
                p_draw.text((x + 25, y + 25), "O", font=font_small, fill=(255, 255, 255, 50))

        # ================= PREBUILD STRIPES =================
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

        # ================= AVATAR =================
        async with aiohttp.ClientSession() as session:
            async with session.get(member.display_avatar.url) as resp:
                avatar_bytes = await resp.read()

        avatar = Image.open(io.BytesIO(avatar_bytes)).convert("RGBA")
        avatar = avatar.resize((110, 110))

        mask = Image.new("L", (110, 110), 0)
        ImageDraw.Draw(mask).ellipse((0, 0, 110, 110), fill=255)
        avatar.putalpha(mask)

        # ================= TYPEWRITER SPEED (OPTIMIZED) =================
        typing_speed = 4
        deleting_speed = 2
        pause_after_type = 12
        pause_after_delete = 4

        timeline = []
        current_frame = 0

        for word in words:
            for i in range(1, len(word) + 1):
                timeline.append((current_frame, word[:i]))
                current_frame += typing_speed

            current_frame += pause_after_type

            for i in range(len(word), 0, -1):
                timeline.append((current_frame, word[:i]))
                current_frame += deleting_speed

            current_frame += pause_after_delete

        total_frames = current_frame + 10

        # ================= FRAME LOOP =================
        for frame in range(total_frames):

            img = base_bg.copy()
            draw = ImageDraw.Draw(img)

            # Pattern animation
            offset = (frame * 4) % spacing
            cropped_pattern = pattern_layer.crop((offset, 0, offset + width, height))
            img = Image.alpha_composite(img, cropped_pattern)

            # Stripes animation
            stripe_offset = (frame * 6) % stripe_spacing
            cropped_stripes = stripe_canvas.crop(
                (stripe_spacing - stripe_offset, 0,
                 stripe_spacing - stripe_offset + width, height)
            )
            img = Image.alpha_composite(img, cropped_stripes)

            draw = ImageDraw.Draw(img)

            # Current text
            welcome_text = ""
            for trigger_frame, text in timeline:
                if frame >= trigger_frame:
                    welcome_text = text
                else:
                    break

            if frame % 20 < 10:
                welcome_text += "|"

            clean_text = welcome_text.replace("|", "")

            if clean_text and clean_text in arabic_word:
                draw.text((60, 40), welcome_text, font=font_arabic, fill=(255, 255, 255))
            elif any("\u3040" <= c <= "\u30ff" for c in clean_text):
                draw.text((60, 60), welcome_text, font=font_jp, fill=(255, 255, 255))
            else:
                draw.text((60, 60), welcome_text, font=font_title, fill=(255, 255, 255))

            # User info
            draw.text((200, 150), username, font=font_user, fill=(255, 255, 255))
            draw.text((200, 200), member_count, font=font_small, fill=(230, 230, 255))
            draw.text((200, 230), join_time, font=font_small, fill=(230, 230, 255))

            img.paste(avatar, (60, 150), avatar)

            # Logo (no blur)
            letter_spacing = -8
            a_width = draw.textlength("A", font=font_logo)
            as_x = width - a_width - draw.textlength("S", font=font_logo) - 140
            as_y = 40

            draw.text((as_x, as_y - 12), "A", font=font_logo, fill=(255, 255, 255))
            draw.text((as_x + a_width + letter_spacing, as_y), "S", font=font_logo, fill=(255, 255, 255))

            draw.text(
                (as_x - 100, as_y + 115),
                "https://discord.gg/arabsstudio",
                font=font_link,
                fill=(255, 255, 255, 160)
            )

            frames.append(img.convert("P", palette=Image.ADAPTIVE))

        gif_path = f"welcome_{member.id}.gif"

        frames[0].save(
            gif_path,
            save_all=True,
            append_images=frames[1:],
            duration=80,
            loop=0,
            disposal=2
        )

        return gif_path

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