import os

import discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
LOBBY_CHANNEL_ID = int(os.getenv("LOBBY_CHANNEL_ID"))
CATEGORY_ID = int(os.getenv("CATEGORY_ID"))

intents = discord.Intents.default()
intents.voice_states = True
intents.members = True
intents.message_content = False


class BBYOBot(commands.Bot):
    def __init__(self) -> None:
        super().__init__(command_prefix="!", intents=intents)
        self.temp_channels: dict[int, int] = {}
        self.lobby_channel_id = LOBBY_CHANNEL_ID
        self.category_id = CATEGORY_ID

    async def setup_hook(self) -> None:
        for extension in [
            "cogs.voice",
            "cogs.coins",
            "cogs.casino_base",
            "cogs.casino_coinflip",
            "cogs.casino_slots",
            "cogs.casino_roulette",
            "cogs.casino_blackjack",
        ]:
            await self.load_extension(extension)

        await self.tree.sync()
        print("Slash commands synced.")

    async def on_ready(self) -> None:
        print(f"Logged in as {self.user} (ID: {self.user.id})")
        print(f"Watching lobby channel ID: {self.lobby_channel_id}")


bot = BBYOBot()

bot.run(TOKEN)
