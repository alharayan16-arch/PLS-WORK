import discord
from discord.ext import commands

REVIEW_CHANNEL_ID = 123456789012345678  # 🔥 PUT REVIEW CHANNEL ID
STAFF_ROLE_ID = 987654321098765432     # 🔥 PUT STAFF ROLE ID


QUESTIONS = [
    "1️⃣ How old are you?",
    "2️⃣ What timezone are you in?",
    "3️⃣ How active are you per day/week?",
    "4️⃣ Have you read and understood the server rules?",
    "5️⃣ Have you been staff before? If yes, where and what role?",
    "6️⃣ Do you have experience with moderation bots (Dyno, Carl-bot, etc.)?",
    "7️⃣ Why should we choose you over other applicants?",
    "8️⃣ A member is spamming but says they’re 'just joking.' What do you do?",
    "9️⃣ Two members are arguing and it’s getting heated. How do you handle it?",
    "🔟 Another staff member is abusing power. What would you do?",
    "1️⃣1️⃣ A friend breaks the rules. How do you respond?"
]


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
        await interaction.followup.send("✅ Applicant accepted.")

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
        await interaction.followup.send("❌ Applicant denied.")


class ApplyView(discord.ui.View):
    @discord.ui.button(label="📝 Apply for Staff", style=discord.ButtonStyle.primary)
    async def apply_button(self, interaction: discord.Interaction, button: discord.ui.Button):

        await interaction.response.defer(ephemeral=True)

        thread = await interaction.channel.create_thread(
            name=f"Application - {interaction.user}",
            type=discord.ChannelType.private_thread
        )

        await thread.add_user(interaction.user)

        await interaction.followup.send(
            "✅ Application thread created! Check it.",
            ephemeral=True
        )

        answers = []

        def check(m):
            return m.author == interaction.user and m.channel == thread

        for question in QUESTIONS:
            await thread.send(question)

            try:
                msg = await interaction.client.wait_for(
                    "message",
                    check=check,
                    timeout=300
                )
                answers.append(msg.content)
            except:
                await thread.send("⏰ Application timed out.")
                return

        embed = discord.Embed(
            title="📩 New Staff Application",
            color=discord.Color.blue()
        )

        embed.add_field(name="Applicant", value=interaction.user.mention, inline=False)

        for i, answer in enumerate(answers):
            embed.add_field(
                name=QUESTIONS[i],
                value=answer,
                inline=False
            )

        review_channel = interaction.guild.get_channel(REVIEW_CHANNEL_ID)

        if review_channel:
            await review_channel.send(
                embed=embed,
                view=ReviewView(interaction.user)
            )

        await thread.send("✅ Application submitted successfully!")
        await thread.edit(locked=True)


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