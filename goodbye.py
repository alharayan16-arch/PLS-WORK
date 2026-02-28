import discord
from discord.ext import commands
from PIL import Image, ImageDraw, ImageFont
import datetime
import aiohttp
import io
import os
import arabic_reshaper
from bidi.algorithm import get_display

GOODBYE_CHANNEL_ID = 1473690582756098231


class Goodbye(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    async def create_goodbye_gif(self, member):

        width, height = 900, 350
        frames = []

        font_title = ImageFont.truetype("NotoSans-Bold.ttf", 70)
        font_user = ImageFont.truetype("NotoSans-Regular.ttf", 40)
        font_small = ImageFont.truetype("NotoSans-Regular.ttf", 28)

        font_arabic = ImageFont.truetype("NotoSansArabic_Condensed-Bold.ttf", 70)
        font_jp = ImageFont.truetype("NotoSansJP-Bold.ttf", 70)

        words = [
            "GOODBYE",
            "AUF WIEDERSEHEN",
            "AU REVOIR",
            "HOŞÇA KAL",
            "ARRIVEDERCI",
            "さようなら"
        ]

        arabic_full = "مع السلامة"
        reshaped = arabic_reshaper.reshape(arabic_full)
        arabic_word = get_display(reshaped)
        words.append(arabic_word)

        username = member.display_name
        member_count = f"Member #{member.guild.member_count}"
        leave_time = datetime.datetime.now(datetime.timezone.utc).strftime("%H:%M UTC")

        base_bg = Image.new("RGBA", (width, height), (40, 0, 80))

        async with aiohttp.ClientSession() as session:
            async with session.get(member.display_avatar.url) as resp:
                avatar_bytes = await resp.read()

        avatar = Image.open(io.BytesIO(avatar_bytes)).convert("RGBA")
        avatar = avatar.resize((110, 110))

        mask = Image.new("L", (110, 110), 0)
        ImageDraw.Draw(mask).ellipse((0, 0, 110, 110), fill=255)
        avatar.putalpha(mask)

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

        for frame in range(total_frames):

            img = base_bg.copy()
            draw = ImageDraw.Draw(img)

            goodbye_text = ""
            for trigger_frame, text in timeline:
                if frame >= trigger_frame:
                    goodbye_text = text
                else:
                    break

            if frame % 20 < 10:
                goodbye_text += "|"

            clean_text = goodbye_text.replace("|", "")

            if clean_text and clean_text in arabic_word:
                draw.text((60, 10), goodbye_text, font=font_arabic, fill=(255, 255, 255))
            elif any("\u3040" <= c <= "\u30ff" for c in clean_text):
                draw.text((60, 10), goodbye_text, font=font_jp, fill=(255, 255, 255))
            else:
                draw.text((60, 10), goodbye_text, font=font_title, fill=(255, 255, 255))

            img.paste(avatar, (60, 75), avatar)

            draw.text((200, 75), username, font=font_user, fill=(255, 255, 255))
            draw.text((200, 115), member_count, font=font_small, fill=(230, 230, 255))
            draw.text((200, 145), leave_time, font=font_small, fill=(230, 230, 255))

            frames.append(img.convert("P", palette=Image.ADAPTIVE))

        gif_path = f"goodbye_{member.id}.gif"

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
    async def on_member_remove(self, member):

        channel = self.bot.get_channel(GOODBYE_CHANNEL_ID)
        if not channel:
            return

        gif_path = await self.create_goodbye_gif(member)

        await channel.send(
            content=f"{member.display_name} has left Arab’s Studio. We hope you enjoyed your stay!",
            file=discord.File(gif_path)
        )

        os.remove(gif_path)


async def setup(bot):
    await bot.add_cog(Goodbye(bot))