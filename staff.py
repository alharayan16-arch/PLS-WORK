import discord
from discord.ext import commands

REVIEW_CHANNEL_ID = 1474454840229892199  # 🔥 PUT REVIEW CHANNEL ID
STAFF_ROLE_ID = 1472767129345327147     # 🔥 PUT STAFF ROLE ID


class ReviewView(discord.ui.View):
    def __init__(self, applicant: discord.Member):
        super().__init__(timeout=None)
        self.applicant = applicant

    @discord.ui.button(label="✅ Accept", style=discord.ButtonStyle.success)
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):

        role = interaction.guild.get_role(STAFF_ROLE_ID)

        if role:
            await self.applicant.add_roles(role)

        # DM user
        try:
            await self.applicant.send(
                f"🎉 Congratulations! You have been accepted as staff in **{interaction.guild.name}**!"
            )
        except:
            pass

        # Disable buttons
        for item in self.children:
            item.disabled = True

        await interaction.response.edit_message(view=self)
        await interaction.followup.send("✅ Applicant accepted.", ephemeral=True)

    @discord.ui.button(label="❌ Deny", style=discord.ButtonStyle.danger)
    async def deny(self, interaction: discord.Interaction, button: discord.ui.Button):

        try:
            await self.applicant.send(
                f"❌ Unfortunately, your staff application in **{interaction.guild.name}** was denied."
            )
        except:
            pass

        for item in self.children:
            item.disabled = True

        await interaction.response.edit_message(view=self)
        await interaction.followup.send("❌ Applicant denied.", ephemeral=True)


class StaffApplicationModal(discord.ui.Modal, title="Staff Application"):

    age = discord.ui.TextInput(label="Your Age")
    timezone = discord.ui.TextInput(label="Your Timezone")
    experience = discord.ui.TextInput(
        label="Past Experience",
        style=discord.TextStyle.paragraph
    )
    reason = discord.ui.TextInput(
        label="Why should we pick you?",
        style=discord.TextStyle.paragraph
    )

    async def on_submit(self, interaction: discord.Interaction):

        embed = discord.Embed(
            title="📩 New Staff Application",
            color=discord.Color.blue()
        )

        embed.add_field(name="Applicant", value=interaction.user.mention, inline=False)
        embed.add_field(name="Age", value=self.age.value, inline=False)
        embed.add_field(name="Timezone", value=self.timezone.value, inline=False)
        embed.add_field(name="Experience", value=self.experience.value, inline=False)
        embed.add_field(name="Why Pick Them?", value=self.reason.value, inline=False)

        channel = interaction.client.get_channel(REVIEW_CHANNEL_ID)

        if channel:
            await channel.send(
                embed=embed,
                view=ReviewView(interaction.user)
            )

        await interaction.response.send_message(
            "✅ Your application has been submitted!",
            ephemeral=True
        )


class ApplyView(discord.ui.View):

    @discord.ui.button(
        label="📝 Apply for Staff",
        style=discord.ButtonStyle.primary
    )
    async def apply_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(StaffApplicationModal())


class Staff(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def staffpanel(self, ctx):
        await ctx.send(
            "Click below to apply for staff:",
            view=ApplyView()
        )


async def setup(bot):
    await bot.add_cog(Staff(bot))