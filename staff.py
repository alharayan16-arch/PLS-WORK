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
            try:
                await self.applicant.add_roles(role)
            except Exception as e:
                print(e)

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


# ================= MODAL 1 (First 5 Questions) =================

class ModalOne(discord.ui.Modal, title="Staff Application (1/2)"):

    q1 = discord.ui.TextInput(label="How old are you?")
    q2 = discord.ui.TextInput(label="What timezone are you in?")
    q3 = discord.ui.TextInput(label="How active are you per day/week?")
    q4 = discord.ui.TextInput(label="Have you read and understood the server rules?")
    q5 = discord.ui.TextInput(label="Have you been staff before? If yes, where and what role?")

    async def on_submit(self, interaction: discord.Interaction):
        data = {
            "How old are you?": self.q1.value,
            "What timezone are you in?": self.q2.value,
            "How active are you per day/week?": self.q3.value,
            "Read and understood rules?": self.q4.value,
            "Previous staff experience?": self.q5.value,
        }

        await interaction.response.send_modal(ModalTwo(data))


# ================= MODAL 2 (Remaining 6 Questions) =================

class ModalTwo(discord.ui.Modal, title="Staff Application (2/2)"):

    def __init__(self, previous_answers):
        super().__init__()
        self.previous_answers = previous_answers

        self.q6 = discord.ui.TextInput(
            label="Experience with moderation bots (Dyno, Carl-bot, etc.)?"
        )
        self.q7 = discord.ui.TextInput(
            label="Why should we choose you over others?",
            style=discord.TextStyle.paragraph
        )
        self.q8 = discord.ui.TextInput(
            label="Member spamming but 'joking' — what do you do?",
            style=discord.TextStyle.paragraph
        )
        self.q9 = discord.ui.TextInput(
            label="Two members arguing — how do you handle it?",
            style=discord.TextStyle.paragraph
        )
        self.q10 = discord.ui.TextInput(
            label="Staff abusing power — what would you do?",
            style=discord.TextStyle.paragraph
        )

        self.q11 = discord.ui.TextInput(
            label="A friend breaks the rules — how do you respond?",
            style=discord.TextStyle.paragraph
        )

        # Add only first 5 to modal (Discord limit)
        self.add_item(self.q6)
        self.add_item(self.q7)
        self.add_item(self.q8)
        self.add_item(self.q9)
        self.add_item(self.q10)

    async def on_submit(self, interaction: discord.Interaction):

        # Save first 10 answers
        data = self.previous_answers
        data.update({
            "Bot experience?": self.q6.value,
            "Why choose you?": self.q7.value,
            "Spamming scenario?": self.q8.value,
            "Argument scenario?": self.q9.value,
            "Staff abuse scenario?": self.q10.value,
        })

        # Since Discord only allows 5 per modal,
        # we collect question 11 through ephemeral reply

        await interaction.response.send_message(
            "Final Question:\n\nA friend breaks the rules — how do you respond?",
            ephemeral=True
        )

        def check(m):
            return m.author == interaction.user and m.channel == interaction.channel

        try:
            msg = await interaction.client.wait_for("message", check=check, timeout=300)
            data["Friend breaks rules?"] = msg.content
        except:
            return

        embed = discord.Embed(
            title="📩 New Staff Application",
            color=discord.Color.blue()
        )

        embed.add_field(name="Applicant", value=interaction.user.mention, inline=False)

        for question, answer in data.items():
            embed.add_field(name=question, value=answer, inline=False)

        review_channel = interaction.guild.get_channel(REVIEW_CHANNEL_ID)
        if review_channel:
            await review_channel.send(embed=embed, view=ReviewView(interaction.user))

        await interaction.followup.send(
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