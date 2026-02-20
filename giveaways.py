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

    # ================= TIME PARSER =================

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

    # ================= RESUME AFTER RESTART =================

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

        @discord.ui.button(
            label="✨ Join Giveaway",
            style=discord.ButtonStyle.success,
            emoji="🎉"
        )
        async def enter(self, interaction: discord.Interaction, button: discord.ui.Button):

            data = self.cog.load_giveaways()

            if self.giveaway_id not in data:
                await interaction.response.send_message("Giveaway not found.", ephemeral=True)
                return

            giveaway = data[self.giveaway_id]

            if giveaway["ended"]:
                await interaction.response.send_message("This giveaway has ended.", ephemeral=True)
                return

            # 7 day anti-alt
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

            await interaction.response.send_message(
                "🔥 You have successfully entered the giveaway!",
                ephemeral=True
            )

    # ================= GIVEAWAY COMMAND =================

    @discord.app_commands.command(name="giveaway", description="Start a premium giveaway")
    async def giveaway(self, interaction: discord.Interaction,
                       duration: str,
                       winners: int,
                       prize: str,
                       requirements: str = "None"):

        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message(
                "You need Manage Server permission.",
                ephemeral=True
            )
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

        embed = discord.Embed(
            title="🎉✨ ARAB'S STUDIO GIVEAWAY ✨🎉",
            color=discord.Color.from_rgb(138, 43, 226)
        )

        embed.description = f"""
🎁 **Prize**
> {prize}

👑 **Winners**
> {winners}

📋 **Requirements**
> {requirements}

⏳ **Ends**
> <t:{end_time}:R>

🔥 Click the button below to enter!
"""

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

    # ================= WAIT AND END =================

    async def wait_and_end(self, giveaway_id):

        data = self.load_giveaways()
        giveaway = data.get(giveaway_id)
        if not giveaway:
            return

        remaining = giveaway["end_time"] - int(datetime.datetime.utcnow().timestamp())
        if remaining > 0:
            await asyncio.sleep(remaining)

        await self.end_giveaway(giveaway_id)

    # ================= END GIVEAWAY =================

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
            title="🏆 GIVEAWAY ENDED 🏆",
            color=discord.Color.gold()
        )

        embed.description = f"""
🎁 **Prize**
> {giveaway['prize']}

👑 **Winner(s)**
> {winner_mentions}

🎉 Congratulations!
"""

        await message.edit(embed=embed, view=None)

        # DM winners
        for winner_id in winners:
            try:
                user = await self.bot.fetch_user(winner_id)

                win_embed = discord.Embed(
                    title="🎉 YOU WON THE GIVEAWAY! 🎉",
                    color=discord.Color.gold()
                )

                win_embed.description = f"""
🏆 **Prize**
> {giveaway['prize']}

📩 **Claim**
> Create a ticket in <#{SUPPORT_CHANNEL_ID}>

⏳ You have limited time before reroll.
"""

                await user.send(embed=win_embed)

            except:
                pass

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

                # DM old winners
                for old in old_winners:
                    if old not in new_winners:
                        try:
                            user = await self.bot.fetch_user(old)

                            reroll_dm = discord.Embed(
                                title="⚠️ Giveaway Rerolled",
                                color=discord.Color.red()
                            )

                            reroll_dm.description = """
🚫 You did not claim your reward in time.

The giveaway has been rerolled and a new winner was selected.
"""

                            await user.send(embed=reroll_dm)

                        except:
                            pass

                channel = self.bot.get_channel(giveaway["channel_id"])
                message = await channel.fetch_message(giveaway["message_id"])

                reroll_embed = discord.Embed(
                    title="🔄 GIVEAWAY REROLLED 🔄",
                    color=discord.Color.orange()
                )

                reroll_embed.description = f"""
🎁 **Prize**
> {giveaway['prize']}

👑 **New Winner(s)**
> {winner_mentions}

⚡ Previous winner did not claim in time.
"""

                reroll_embed.set_footer(
                    text=f"Rerolled by {interaction.user}",
                    icon_url=interaction.user.display_avatar.url
                )

                await message.edit(embed=reroll_embed, view=None)

                await interaction.followup.send(
                    "Giveaway rerolled successfully.",
                    ephemeral=True
                )
                return

        await interaction.followup.send("Giveaway not found.", ephemeral=True)


async def setup(bot):
    await bot.add_cog(Giveaways(bot))