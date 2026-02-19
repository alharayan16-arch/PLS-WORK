@bot.tree.command(name="reroll", description="Reroll a giveaway")
async def reroll(interaction: discord.Interaction, message_id: str):

    if not interaction.user.guild_permissions.manage_guild:
        await interaction.response.send_message("Need Manage Server permission.", ephemeral=True)
        return

    data = load_giveaways()

    for gid, giveaway in data.items():
        if str(giveaway["message_id"]) == message_id and giveaway["ended"]:

            channel = bot.get_channel(giveaway["channel_id"])
            message = await channel.fetch_message(giveaway["message_id"])

            old_winners = giveaway.get("last_winners", [])

            if len(giveaway["entries"]) == 0:
                await interaction.response.send_message("No entries to reroll.", ephemeral=True)
                return

            new_winners = random.sample(
                giveaway["entries"],
                min(giveaway["winners"], len(giveaway["entries"]))
            )

            giveaway["last_winners"] = new_winners
            save_giveaways(data)

            # DM OLD winners
            for old in old_winners:
                try:
                    user = await bot.fetch_user(old)
                    embed = discord.Embed(
                        title="⚠️ Giveaway Update",
                        description="You did not claim your reward in time. The giveaway has been rerolled.",
                        color=discord.Color.red()
                    )
                    await user.send(embed=embed)
                except:
                    pass

            # DM NEW winners
            for winner_id in new_winners:
                try:
                    user = await bot.fetch_user(winner_id)
                    embed = discord.Embed(
                        title="🎉 YOU WON!",
                        color=GW_COLOR
                    )
                    embed.add_field(
                        name="🏆 Prize",
                        value=f"**{giveaway['prize']}**",
                        inline=False
                    )
                    embed.add_field(
                        name="📩 Claim",
                        value=f"Create a ticket in <#{SUPPORT_CHANNEL_ID}>",
                        inline=False
                    )
                    await user.send(embed=embed)
                except:
                    pass

            # Edit giveaway message
            winner_mentions = " ".join(f"<@{w}>" for w in new_winners)

            embed = discord.Embed(
                title="🎉 GIVEAWAY REROLLED",
                color=GW_COLOR
            )
            embed.add_field(name="🎁 Prize", value=giveaway["prize"], inline=False)
            embed.add_field(name="👥 Entries", value=len(giveaway["entries"]), inline=True)
            embed.add_field(name="🏆 New Winner(s)", value=winner_mentions, inline=False)

            await message.edit(embed=embed, view=None)

            # Staff log
            staff = bot.get_channel(STAFF_LOG_CHANNEL_ID)
            if staff:
                log_embed = discord.Embed(
                    title="🔄 Giveaway Rerolled",
                    color=GW_COLOR
                )
                log_embed.add_field(name="Prize", value=giveaway["prize"])
                log_embed.add_field(name="New Winners", value=winner_mentions)
                await staff.send(embed=log_embed)

            await interaction.response.send_message("Giveaway rerolled successfully.")
            return

    await interaction.response.send_message("Giveaway not found.", ephemeral=True)
