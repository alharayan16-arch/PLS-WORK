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
STAFF_LOG_CHANNEL_ID = 1473910880264519730
GW_COLOR = discord.Color(0x5E17EB)


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

    def format_duration(self, seconds):
        h = seconds // 3600
        m = (seconds % 3600) // 60
        s = seconds % 60
        parts = []
        if h > 0: parts.append(f"{h}h")
        if m > 0: parts.append(f"{m}m")
        if s > 0: parts.append(f"{s}s")
        return " ".join(parts) if parts else "0s"

    # ================= RESUME ON RESTART =================

    async def resume_giveaways(self):
        await self.bot.wait_until_ready()
        data = self.load_giveaways()

        for gid, giveaway in data.items():
            if not giveaway.get("ended", True):
                self.bot.loop.create_task(self.countdown_loop(gid))

    # ================= GIVEAWAY VIEW =================

    class GiveawayView(discord.ui.View):
        def __init__(self, cog, giveaway_id):
            super().__init__(timeout=None)
            self.cog = cog
            self.giveaway_id = giveaway_id

        @discord.ui.button(label="🎉 Enter Giveaway (0)", style=discord.ButtonStyle.primary)
        async def enter(self, interaction: discord.Interaction, button: discord.ui.Button):

            data = self.cog.load_giveaways()

            if self.giveaway_id not in data:
                await interaction.response.send_message("Giveaway not found.", ephemeral=True)
                return

            giveaway = data[self.giveaway_id]

            if giveaway["ended"]:
                await interaction.response.send_message("This giveaway has ended.", ephemeral=True)
                return

            # Anti-alt: 7 day account age
            min_age = datetime.timedelta(days=7)
            if datetime.datetime.utcnow() - interaction.user.created_at.replace(tzinfo=None) < min_age:
                await interaction.response.send_message(
                    "Your account must be at least 7 days old to enter.",
                    ephemeral=True
                )
                return

            if interaction.user.id in giveaway["entries"]:
                await interaction.response.send_message("You already entered.", ephemeral=True)
                return

            giveaway["entries"].append(interaction.user.id)
            self.cog.save_giveaways(data)

            button.label = f"🎉 Enter Giveaway ({len(giveaway['entries'])})"
            await interaction.message.edit(view=self)

            await interaction.response.send_message("You entered the giveaway!", ephemeral=True)

    # ================= GIVEAWAY COMMAND =================

    @discord.app_commands.command(name="giveaway", description="Start a giveaway")
    async def giveaway(self, interaction: discord.Interaction,
                       duration: str,
                       winners: int,
                       prize: str,
                       requirements: str = "None"):

        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message("You need Manage Server permission.", ephemeral=True)
            return

        duration_seconds = self.parse_duration(duration)
        if not duration_seconds:
            await interaction.response.send_message(
                "Invalid duration format. Example: 1h30m, 5m, 30s",
                ephemeral=True
            )
            return

        giveaway_id = str(interaction.id)
        end_time = int(datetime.datetime.utcnow().timestamp()) + duration_seconds

        embed = discord.Embed(title="✨ ARAB'S STUDIO GIVEAWAY ✨", color=GW_COLOR)
        embed.add_field(name="🎁 Prize", value=f"**{prize}**", inline=False)
        embed.add_field(name="👥 Winners", value=str(winners), inline=True)
        embed.add_field(name="📌 Requirements", value=requirements, inline=True)
        embed.add_field(name="⏳ Ends In", value=self.format_duration(duration_seconds), inline=False)

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

        self.bot.loop.create_task(self.countdown_loop(giveaway_id))

    # ================= COUNTDOWN =================

    async def countdown_loop(self, giveaway_id):

        while True:
            await asyncio.sleep(30)

            data = self.load_giveaways()
            if giveaway_id not in data:
                return

            giveaway = data[giveaway_id]
            if giveaway["ended"]:
                return

            remaining = giveaway["end_time"] - int(datetime.datetime.utcnow().timestamp())

            if remaining <= 0:
                await self.end_giveaway(giveaway_id)
                return

            try:
                channel = self.bot.get_channel(giveaway["channel_id"])
                message = await channel.fetch_message(giveaway["message_id"])

                embed = message.embeds[0]
                embed.set_field_at(3, name="⏳ Ends In",
                                   value=self.format_duration(remaining),
                                   inline=False)

                await message.edit(embed=embed)
            except:
                return

    # ================= END GIVEAWAY =================

    async def end_giveaway(self, giveaway_id):

        data = self.load_giveaways()
        if giveaway_id not in data:
            return

        giveaway = data[giveaway_id]
        giveaway["ended"] = True

        channel = self.bot.get_channel(giveaway["channel_id"])
        message = await channel.fetch_message(giveaway["message_id"])

        entries = giveaway["entries"]
        winners = []

        if entries:
            winners = random.sample(entries, min(giveaway["winners"], len(entries)))

        giveaway["last_winners"] = winners
        self.save_giveaways(data)

        winner_mentions = "None"
        if winners:
            winner_mentions = " ".join(f"<@{w}>" for w in winners)

        embed = discord.Embed(title="🎉 GIVEAWAY ENDED", color=GW_COLOR)
        embed.add_field(name="🎁 Prize", value=giveaway["prize"], inline=False)
        embed.add_field(name="👥 Entries", value=len(entries), inline=True)
        embed.add_field(name="🏆 Winner(s)", value=winner_mentions, inline=False)

        await message.edit(embed=embed, view=None)

        staff = self.bot.get_channel(STAFF_LOG_CHANNEL_ID)
        if staff:
            log = discord.Embed(title="🏆 Giveaway Ended", color=GW_COLOR)
            log.add_field(name="Prize", value=giveaway["prize"])
            log.add_field(name="Winners", value=winner_mentions)
            await staff.send(embed=log)

    # ================= REROLL =================

    @discord.app_commands.command(name="reroll", description="Reroll a giveaway")
    async def reroll(self, interaction: discord.Interaction, message_id: str):

        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message(
                "You need Manage Server permission.",
                ephemeral=True
            )
            return

        await interaction.response.defer(ephemeral=True)

        data = self.load_giveaways()

        for gid, giveaway in data.items():
            if str(giveaway["message_id"]) == message_id and giveaway["ended"]:

                entries = giveaway["entries"]
                old_winners = giveaway.get("last_winners", [])

                available = [e for e in entries if e not in old_winners]

                if not available:
                    await interaction.followup.send(
                        "No new eligible users to reroll.",
                        ephemeral=True
                    )
                    return

                new_winners = random.sample(
                    available,
                    min(giveaway["winners"], len(available))
                )

                giveaway["last_winners"] = new_winners
                self.save_giveaways(data)

                winner_mentions = " ".join(f"<@{w}>" for w in new_winners)

                channel = self.bot.get_channel(giveaway["channel_id"])
                message = await channel.fetch_message(giveaway["message_id"])

                embed = discord.Embed(title="🎉 GIVEAWAY ENDED", color=GW_COLOR)
                embed.add_field(name="🎁 Prize", value=giveaway["prize"], inline=False)
                embed.add_field(name="👥 Entries", value=len(entries), inline=True)
                embed.add_field(name="🏆 Winner(s)", value=winner_mentions, inline=False)
                embed.set_footer(text="🔄 This giveaway has been rerolled.")

                await message.edit(embed=embed)

                await interaction.followup.send(
                    "Giveaway rerolled successfully.",
                    ephemeral=True
                )
                return

        await interaction.followup.send("Giveaway not found.", ephemeral=True)


async def setup(bot):
    await bot.add_cog(Giveaways(bot))