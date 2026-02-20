import discord
from discord.ext import commands
import datetime
import random
import json
import asyncio
import os
import re

GIVEAWAY_FILE = "giveaways.json"
SUPPORT_CHANNEL_ID = 1472228682566340842


class Giveaways(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.bot.loop.create_task(self.resume_giveaways())

    # ================= STORAGE =================

    def load_giveaways(self):
        if not os.path.exists(GIVEAWAY_FILE):
            return {}
        try:
            with open(GIVEAWAY_FILE, "r") as f:
                return json.load(f)
        except:
            return {}

    def save_giveaways(self, data):
        with open(GIVEAWAY_FILE, "w") as f:
            json.dump(data, f, indent=4)

    # ================= TIME =================

    def parse_duration(self, duration: str):
        pattern = r"(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s)?"
        match = re.fullmatch(pattern, duration.lower())
        if not match:
            return None
        h = int(match.group(1)) if match.group(1) else 0
        m = int(match.group(2)) if match.group(2) else 0
        s = int(match.group(3)) if match.group(3) else 0
        total = h * 3600 + m * 60 + s
        return total if total > 0 else None

    async def resume_giveaways(self):
        await self.bot.wait_until_ready()
        data = self.load_giveaways()
        for gid, giveaway in data.items():
            if not giveaway.get("ended", True):
                self.bot.add_view(self.GiveawayView(self, gid))

    # ================= GIVEAWAY VIEW =================

    class GiveawayView(discord.ui.View):
        def __init__(self, cog, giveaway_id):
            super().__init__(timeout=None)
            self.cog = cog
            self.giveaway_id = giveaway_id

        @discord.ui.button(label="🎉 Join", style=discord.ButtonStyle.success)
        async def enter(self, interaction: discord.Interaction, button: discord.ui.Button):

            data = self.cog.load_giveaways()

            if self.giveaway_id not in data:
                await interaction.response.send_message("Giveaway not found.", ephemeral=True)
                return

            giveaway = data[self.giveaway_id]

            if giveaway["ended"]:
                await interaction.response.send_message("This giveaway has ended.", ephemeral=True)
                return

            if interaction.user.id in giveaway["entries"]:
                await interaction.response.send_message("You already entered.", ephemeral=True)
                return

            giveaway["entries"].append(interaction.user.id)
            self.cog.save_giveaways(data)

            # Update embed with entry count
            channel = interaction.channel
            message = await channel.fetch_message(giveaway["message_id"])

            embed = message.embeds[0]
            embed.set_field_at(
                0,
                name="Giveaway Info",
                value=self.cog.build_info_text(giveaway),
                inline=False
            )

            await message.edit(embed=embed)

            await interaction.response.send_message("You're in! 🔥", ephemeral=True)

    # ================= EMBED BUILDER =================

    def build_info_text(self, giveaway):
        return (
            f"🎁 **{giveaway['prize']}**\n"
            f"👑 {giveaway['winners']} Winner(s)\n"
            f"👥 {len(giveaway['entries'])} Entrie(s)\n"
            f"⏳ Ends <t:{giveaway['end_time']}:R>\n\n"
            f"📋 Requirements: {giveaway['requirements']}"
        )

    # ================= GIVEAWAY COMMAND =================

    @discord.app_commands.command(name="giveaway", description="Start a giveaway")
    async def giveaway(self, interaction: discord.Interaction,
                       duration: str,
                       winners: int,
                       prize: str,
                       requirements: str = "None"):

        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message("No permission.", ephemeral=True)
            return

        duration_seconds = self.parse_duration(duration)
        if not duration_seconds:
            await interaction.response.send_message("Invalid duration.", ephemeral=True)
            return

        giveaway_id = str(interaction.id)
        end_time = int(datetime.datetime.utcnow().timestamp()) + duration_seconds

        embed = discord.Embed(
            title="🎉 ARAB'S STUDIO GIVEAWAY",
            color=discord.Color.purple()
        )

        embed.add_field(
            name="Giveaway Info",
            value=(
                f"🎁 **{prize}**\n"
                f"👑 {winners} Winner(s)\n"
                f"👥 0 Entrie(s)\n"
                f"⏳ Ends <t:{end_time}:R>\n\n"
                f"📋 Requirements: {requirements}"
            ),
            inline=False
        )

        embed.set_footer(
            text=f"Hosted by {interaction.user}",
            icon_url=interaction.user.display_avatar.url
        )

        view = self.GiveawayView(self, giveaway_id)

        await interaction.response.send_message(embed=embed, view=view)
        message = await interaction.original_response()

        data = self.load_giveaways()
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
        self.save_giveaways(data)

        self.bot.loop.create_task(self.wait_and_end(giveaway_id))

    # ================= END GIVEAWAY =================

    async def wait_and_end(self, giveaway_id):
        data = self.load_giveaways()
        giveaway = data.get(giveaway_id)
        if not giveaway:
            return

        remaining = giveaway["end_time"] - int(datetime.datetime.utcnow().timestamp())
        if remaining > 0:
            await asyncio.sleep(remaining)

        await self.end_giveaway(giveaway_id)

    async def end_giveaway(self, giveaway_id):

        data = self.load_giveaways()
        giveaway = data.get(giveaway_id)
        if not giveaway:
            return

        giveaway["ended"] = True
        entries = giveaway["entries"]

        winners = []
        if entries:
            winners = random.sample(entries, min(giveaway["winners"], len(entries)))

        giveaway["last_winners"] = winners
        self.save_giveaways(data)

        winner_mentions = "None"
        if winners:
            winner_mentions = " ".join(f"<@{w}>" for w in winners)

        channel = self.bot.get_channel(giveaway["channel_id"])
        message = await channel.fetch_message(giveaway["message_id"])

        embed = discord.Embed(
            title="🏆 GIVEAWAY ENDED",
            description=(
                f"🎁 **{giveaway['prize']}**\n"
                f"👑 {winner_mentions}\n"
                f"👥 {len(entries)} Entrie(s)"
            ),
            color=discord.Color.gold()
        )

        await message.edit(embed=embed, view=None)


async def setup(bot):
    await bot.add_cog(Giveaways(bot))