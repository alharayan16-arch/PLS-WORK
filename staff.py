import discord
from discord.ext import commands

REVIEW_CHANNEL_ID = 1474454840229892199  # PUT REVIEW CHANNEL ID
STAFF_ROLE_ID = 1472767129345327147     # PUT STAFF ROLE ID


# ================= REVIEW BUTTONS =================

class ReviewView(discord.ui.View):
    def __init__(self, applicant: discord.Member):
        super().__init__(timeout=None)
        self.applicant = applicant

    @discord.ui.button(label="✅ Accept", style=discord.ButtonStyle.success)
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)

        role = interaction.guild.get_role(STAFF_ROLE_ID)
        if role:
            await self.applicant.add_roles(role)

        try:
            await self.applicant.send(
                f"🎉 You have been accepted as staff in **{interaction.guild.name}**!"
            )
        except:
            pass

        for item in self.children:
            item.disabled = True

        await interaction.message.edit(view=self)
        await interaction.followup.send("Applicant accepted.")

    @discord.ui.button(label="❌ Deny", style=discord.ButtonStyle.danger)
    async def deny(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)

        try:
            await self.applicant.send(
                f"❌ Your staff application in **{interaction.guild.name}** was denied."
            )
        except:
            pass

        for item in self.children:
            item.disabled = True

        await interaction.message.edit(view=self)
        await interaction.followup.send("Applicant denied.")


# ================= MODAL 1 =================

class ModalOne(discord.ui.Modal, title="Staff Application (1/3)"):

    q1 = discord.ui.TextInput(label="How old are you?")
    q2 = discord.ui.TextInput(label="What timezone are you in?")
    q3 = discord.ui.TextInput(label="How active are you per day/week?")
    q4 = discord.ui.TextInput(label="Have you read and understood the server rules?")
    q5 = discord.ui.TextInput(label="Have you been staff before? If yes, where and what role?")

    async def on_submit(self, interaction: discord.Interaction):
        data = {
            "q1": self.q1.value,
            "q2": self.q2.value,
            "q3": self.q3.value,
            "q4": self.q4.value,
            "q5": self.q5.value,
        }

        await interaction.response.send_modal(ModalTwo(data))


# ================= MODAL 2 =================

class ModalTwo(discord.ui.Modal, title="Staff Application (2/3)"):

    def __init__(self, previous_answers):
        super().__init__()
        self.previous_answers = previous_answers

    q6 = discord.ui.TextInput(label="Experience with moderation bots?")
    q7 = discord.ui.TextInput(label="Why should we choose you?", style=discord.TextStyle.paragraph)
    q8 = discord.ui.TextInput(label="Member spamming but 'joking' — what do you do?", style=discord.TextStyle.paragraph)
    q9 = discord.ui.TextInput(label="Two members arguing — how do you handle it?", style=discord.TextStyle.paragraph)
    q10 = discord.ui.TextInput(label="Staff abusing power — what do you do?", style=discord.TextStyle.paragraph)

    async def on_submit(self, interaction: discord.Interaction):
        data = self.previous_answers
        data.update({
            "q6": self.q6.value,
            "q7": self.q7.value,
            "q8": self.q8.value,
            "q9": self.q9.value,
            "q10": self.q10.value,
        })

        await interaction.response.send_modal(ModalThree(data))


# ================= MODAL 3 =================

class ModalThree(discord.ui.Modal, title="Staff Application (3/3)"):

    def __init__(self, previous_answers):
        super().__init__()
        self.previous_answers = previous_answers

    q11 = discord.ui.TextInput(label="A friend breaks the rules — how do you respond?", style=discord.TextStyle.paragraph)

    async def on_submit(self, interaction: discord.Interaction):

        data = self.previous_answers
        data["q11"] = self.q11.value

        embed = discord.Embed(
            title="📩 New Staff Application",
            color=discord.Color.blue()
        )

        embed.add_field(name="Applicant", value=interaction.user.mention, inline=False)

        questions = [
            "How old are you?",
            "Timezone?",
            "Activity?",
            "Read rules?",
            "Previous staff?",
            "Bot experience?",
            "Why choose you?",
            "Spamming scenario?",
            "Argument scenario?",
            "Staff abuse scenario?",
            "Friend breaks rules?"
        ]

        for i, key in enumerate(data):
            embed.add_field(name=questions[i], value=data[key], inline=False)

        review_channel = interaction.guild.get_channel(REVIEW_CHANNEL_ID)

        if review_channel:
            await review_channel.send(embed=embed, view=ReviewView(interaction.user))

        await interaction.response.send_message(
            "✅ Application submitted successfully!",
            ephemeral=True
        )


# ================= BUTTON =================

class ApplyView(discord.ui.View):
    @discord.ui.button(label="📝 Apply for Staff", style=discord.ButtonStyle.primary)
    async def apply_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ModalOne())


# ================= COG =================

class Staff(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def staffpanel(self, ctx):
        await ctx.send("Click below to apply for staff:", view=ApplyView())


async def setup(bot):
    await bot.add_cog(Staff(bot))