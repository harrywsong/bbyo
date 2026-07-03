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
intents.message_content = True  # needed for prefix commands (!join, !leave)

bot = commands.Bot(command_prefix="!", intents=intents)

# Tracks temp channels: {channel_id: owner_id}
temp_channels: dict[int, int] = {}


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    print(f"Watching lobby channel ID: {LOBBY_CHANNEL_ID}")


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


@bot.command(name="join")
@commands.has_permissions(administrator=True)
async def join(ctx, channel: discord.VoiceChannel = None):
    """Join a voice channel and stay there. Usage: !join #channel-name"""
    target = channel or (ctx.author.voice.channel if ctx.author.voice else None)
    if target is None:
        await ctx.send("Specify a voice channel or join one first.")
        return
    if ctx.voice_client:
        await ctx.voice_client.move_to(target)
    else:
        await target.connect(self_deaf=True)  # self_deaf so it doesn't spam audio
    await ctx.send(f"Joined **{target.name}**.")


@bot.command(name="leave")
@commands.has_permissions(administrator=True)
async def leave(ctx):
    """Leave the current voice channel. Usage: !leave"""
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        await ctx.send("Left the voice channel.")
    else:
        await ctx.send("I'm not in a voice channel.")


bot.run(TOKEN)
