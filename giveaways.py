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
                self.bot.loop.create_task(self.wait_and_end(gid))

    # ================= EMBED =================

    def build_embed(self, giveaway):
        embed = discord.Embed(
            title="🎉 ARAB'S STUDIO GIVEAWAY",
            description=(
                f"🎁 **{giveaway['prize']}**\n"
                f"👑 {giveaway['winners']} Winner(s)\n"
                f"👥 {len(giveaway['entries'])} Entrie(s)\n"
                f"⏳ Ends <t:{giveaway['end_time']}:R>\n\n"
                f"📋 Requirements: {giveaway['requirements']}"
            ),
            color=discord.Color.purple()
        )
        return embed

    # ================= VIEW =================

    class GiveawayView(discord.ui.View):
        def __init__(self, cog, giveaway_id):
            super().__init__(timeout=None)
            self.cog = cog
            self.giveaway_id = giveaway_id

        @discord.ui.button(label="🎉 Join", style=discord.ButtonStyle.success)
        async def enter(self, interaction: discord.Interaction, button: discord.ui.Button):

            data = self.cog.load_giveaways()

            giveaway = data.get(self.giveaway_id)
            if not giveaway or giveaway["ended"]:
                await interaction.response.send_message("Giveaway ended.", ephemeral=True)
                return

            if interaction.user.id in giveaway["entries"]:
                await interaction.response.send_message("Already entered.", ephemeral=True)
                return

            giveaway["entries"].append(interaction.user.id)
            self.cog.save_giveaways(data)

            message = await interaction.channel.fetch_message(giveaway["message_id"])
            embed = self.cog.build_embed(giveaway)
            await message.edit(embed=embed)

            await interaction.response.send_message("You entered!", ephemeral=True)

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

        seconds = self.parse_duration(duration)
        if not seconds:
            await interaction.response.send_message("Invalid duration.", ephemeral=True)
            return

        giveaway_id = str(interaction.id)
        end_time = int(datetime.datetime.utcnow().timestamp()) + seconds

        data = self.load_giveaways()
        data[giveaway_id] = {
            "message_id": None,
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

        embed = self.build_embed(data[giveaway_id])
        view = self.GiveawayView(self, giveaway_id)

        await interaction.response.send_message(embed=embed, view=view)
        message = await interaction.original_response()

        data[giveaway_id]["message_id"] = message.id
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
        if not giveaway or giveaway["ended"]:
            return

        giveaway["ended"] = True
        entries = giveaway["entries"]

        winners = random.sample(entries, min(giveaway["winners"], len(entries))) if entries else []
        giveaway["last_winners"] = winners
        self.save_giveaways(data)

        channel = self.bot.get_channel(giveaway["channel_id"])

        winner_mentions = " ".join(f"<@{w}>" for w in winners) if winners else "No winners"

        # 🔔 NEW PUBLIC MESSAGE (PING WINNER)
        end_embed = discord.Embed(
            title="🏆 GIVEAWAY ENDED",
            description=(
                f"🎁 **{giveaway['prize']}**\n"
                f"👑 Winner(s): {winner_mentions}\n"
                f"👥 {len(entries)} Entries"
            ),
            color=discord.Color.gold()
        )

        await channel.send(content=winner_mentions, embed=end_embed)

        # 📩 DM WINNERS
        for winner_id in winners:
            try:
                user = await self.bot.fetch_user(winner_id)
                dm = discord.Embed(
                    title="🎉 YOU WON!",
                    description=f"Prize: {giveaway['prize']}\nClaim in <#{SUPPORT_CHANNEL_ID}>",
                    color=discord.Color.gold()
                )
                await user.send(embed=dm)
            except:
                pass

        # 📜 STAFF LOG
        staff = self.bot.get_channel(STAFF_LOG_CHANNEL_ID)
        if staff:
            log = discord.Embed(
                title="Giveaway Ended",
                description=f"Prize: {giveaway['prize']}\nWinners: {winner_mentions}",
                color=discord.Color.blue()
            )
            await staff.send(embed=log)

    # ================= REROLL =================

    @discord.app_commands.command(name="reroll", description="Reroll a giveaway")
    async def reroll(self, interaction: discord.Interaction, message_id: str):

        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message("No permission.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        data = self.load_giveaways()

        for gid, giveaway in data.items():
            if str(giveaway["message_id"]) == message_id and giveaway["ended"]:

                entries = giveaway["entries"]
                old_winners = giveaway.get("last_winners", [])

                available = [e for e in entries if e not in old_winners]
                if not available:
                    await interaction.followup.send("No new users to reroll.", ephemeral=True)
                    return

                new_winners = random.sample(
                    available,
                    min(giveaway["winners"], len(available))
                )

                giveaway["last_winners"] = new_winners
                self.save_giveaways(data)

                channel = self.bot.get_channel(giveaway["channel_id"])
                winner_mentions = " ".join(f"<@{w}>" for w in new_winners)

                # 🔔 NEW PUBLIC MESSAGE
                reroll_embed = discord.Embed(
                    title="🔄 GIVEAWAY REROLLED",
                    description=f"🎁 {giveaway['prize']}\n👑 New Winner(s): {winner_mentions}",
                    color=discord.Color.orange()
                )

                await channel.send(content=winner_mentions, embed=reroll_embed)

                # 📩 DM NEW WINNERS
                for w in new_winners:
                    try:
                        user = await self.bot.fetch_user(w)
                        await user.send(embed=discord.Embed(
                            title="🎉 YOU WON (REROLL)!",
                            description=f"Prize: {giveaway['prize']}",
                            color=discord.Color.green()
                        ))
                    except:
                        pass

                # 📩 DM OLD WINNERS
                for old in old_winners:
                    if old not in new_winners:
                        try:
                            user = await self.bot.fetch_user(old)
                            await user.send(embed=discord.Embed(
                                title="⚠️ You Lost The Giveaway",
                                description="The giveaway was rerolled.",
                                color=discord.Color.red()
                            ))
                        except:
                            pass

                # 📜 STAFF LOG
                staff = self.bot.get_channel(STAFF_LOG_CHANNEL_ID)
                if staff:
                    await staff.send(embed=discord.Embed(
                        title="Giveaway Rerolled",
                        description=f"Prize: {giveaway['prize']}\nNew Winners: {winner_mentions}",
                        color=discord.Color.orange()
                    ))

                await interaction.followup.send("Rerolled successfully.", ephemeral=True)
                return

        await interaction.followup.send("Giveaway not found.", ephemeral=True)


async def setup(bot):
    await bot.add_cog(Giveaways(bot))