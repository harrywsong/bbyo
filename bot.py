import discord
from discord.ext import commands
import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
LOBBY_CHANNEL_ID = int(os.getenv("LOBBY_CHANNEL_ID"))  # The "join to create" channel
CATEGORY_ID = int(os.getenv("CATEGORY_ID"))            # Category where temp VCs are created

intents = discord.Intents.default()
intents.voice_states = True
intents.members = True
intents.message_content = False  # not needed for slash commands

bot = commands.Bot(command_prefix="!", intents=intents)

# Tracks temp channels: {channel_id: owner_id}
temp_channels: dict[int, int] = {}


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    print(f"Watching lobby channel ID: {LOBBY_CHANNEL_ID}")
    await bot.tree.sync()
    print("Slash commands synced.")


@bot.event
async def on_voice_state_update(member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
    guild = member.guild

    # ── User joins the lobby channel → create a temp VC ──────────────────────
    if after.channel and after.channel.id == LOBBY_CHANNEL_ID:
        category = guild.get_channel(CATEGORY_ID)
        if category is None:
            print(f"ERROR: Category {CATEGORY_ID} not found.")
            return

        # Create the channel with an overwrites dict that gives the creator admin-like perms
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=True, connect=True),
            member: discord.PermissionOverwrite(
                manage_channels=True,   # rename / edit channel settings
                move_members=True,      # kick/move people out
                mute_members=True,      # mute members in this channel
                deafen_members=True,    # deafen members in this channel
                manage_permissions=True # manage overwrites for this channel
            ),
        }

        channel_name = f"{member.display_name}'s 보이스 채널"
        new_channel = await guild.create_voice_channel(
            name=channel_name,
            category=category,
            overwrites=overwrites,
            reason=f"Temp VC created by {member}",
        )

        temp_channels[new_channel.id] = member.id
        print(f"Created temp VC '{new_channel.name}' (ID: {new_channel.id}) for {member}")

        # Move the creator into their new channel
        await member.move_to(new_channel)

    # ── User leaves a channel → check if it was a temp VC and is now empty ───
    if before.channel and before.channel.id in temp_channels:
        channel = before.channel

        # Re-fetch to get an accurate member count
        channel = guild.get_channel(channel.id)
        if channel is None:
            # Already deleted somehow
            temp_channels.pop(before.channel.id, None)
            return

        if len(channel.members) == 0:
            print(f"Deleting empty temp VC '{channel.name}' (ID: {channel.id})")
            temp_channels.pop(channel.id, None)
            await channel.delete(reason="Temp VC is empty")


@bot.tree.command(name="join", description="Make the bot join a voice channel and stay there.")
@discord.app_commands.checks.has_permissions(administrator=True)
async def join(interaction: discord.Interaction, channel: discord.VoiceChannel = None):
    target = channel or (interaction.user.voice.channel if interaction.user.voice else None)
    if target is None:
        await interaction.response.send_message("Specify a voice channel or join one first.", ephemeral=True)
        return
    if interaction.guild.voice_client:
        await interaction.guild.voice_client.move_to(target)
    else:
        await target.connect(self_deaf=True)
    await interaction.response.send_message(f"Joined **{target.name}**.", ephemeral=True)


@bot.tree.command(name="leave", description="Make the bot leave the current voice channel.")
@discord.app_commands.checks.has_permissions(administrator=True)
async def leave(interaction: discord.Interaction):
    if interaction.guild.voice_client:
        await interaction.guild.voice_client.disconnect()
        await interaction.response.send_message("Left the voice channel.", ephemeral=True)
    else:
        await interaction.response.send_message("I'm not in a voice channel.", ephemeral=True)


bot.run(TOKEN)
