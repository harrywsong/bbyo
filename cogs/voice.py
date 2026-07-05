import discord
from discord.ext import commands


class VoiceCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        print("Voice cog loaded.")

    @commands.Cog.listener()
    async def on_voice_state_update(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ) -> None:
        guild = member.guild

        if after.channel and after.channel.id == self.bot.lobby_channel_id:
            category = guild.get_channel(self.bot.category_id)
            if category is None:
                print(f"ERROR: Category {self.bot.category_id} not found.")
                return

            overwrites = {
                guild.default_role: discord.PermissionOverwrite(view_channel=True, connect=True),
                member: discord.PermissionOverwrite(
                    manage_channels=True,
                    move_members=True,
                    mute_members=True,
                    deafen_members=True,
                    manage_permissions=True,
                ),
            }

            channel_name = f"{member.display_name}'s 보이스 채널"
            new_channel = await guild.create_voice_channel(
                name=channel_name,
                category=category,
                overwrites=overwrites,
                reason=f"Temp VC created by {member}",
            )

            self.bot.temp_channels[new_channel.id] = member.id
            print(f"Created temp VC '{new_channel.name}' (ID: {new_channel.id}) for {member}")
            await member.move_to(new_channel)

        if before.channel and before.channel.id in self.bot.temp_channels:
            channel = guild.get_channel(before.channel.id)
            if channel is None:
                self.bot.temp_channels.pop(before.channel.id, None)
                return

            if len(channel.members) == 0:
                print(f"Deleting empty temp VC '{channel.name}' (ID: {channel.id})")
                self.bot.temp_channels.pop(channel.id, None)
                await channel.delete(reason="Temp VC is empty")

    @discord.app_commands.command(name="join", description="Make the bot join a voice channel and stay there.")
    @discord.app_commands.checks.has_permissions(administrator=True)
    async def join(self, interaction: discord.Interaction, channel: discord.VoiceChannel | None = None) -> None:
        target = channel or (interaction.user.voice.channel if interaction.user.voice else None)
        if target is None:
            await interaction.response.send_message("Specify a voice channel or join one first.", ephemeral=True)
            return

        if interaction.guild and interaction.guild.voice_client:
            await interaction.guild.voice_client.move_to(target)
        else:
            await target.connect(self_deaf=True)

        await interaction.response.send_message(f"Joined **{target.name}**.", ephemeral=True)

    @discord.app_commands.command(name="leave", description="Make the bot leave the current voice channel.")
    @discord.app_commands.checks.has_permissions(administrator=True)
    async def leave(self, interaction: discord.Interaction) -> None:
        if interaction.guild and interaction.guild.voice_client:
            await interaction.guild.voice_client.disconnect()
            await interaction.response.send_message("Left the voice channel.", ephemeral=True)
        else:
            await interaction.response.send_message("I'm not in a voice channel.", ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(VoiceCog(bot))
