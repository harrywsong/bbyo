import os

import discord
from discord import app_commands
from discord.ext import commands


class CasinoBaseCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    def _get_required_channel_id(self, guild_id: int, game_type: str) -> int | None:
        env_key = {
            "coinflip": "CASINO_COINFLIP_CHANNEL_ID",
            "slot_machine": "CASINO_SLOTS_CHANNEL_ID",
            "roulette": "CASINO_ROULETTE_CHANNEL_ID",
            "blackjack": "CASINO_BLACKJACK_CHANNEL_ID",
        }.get(game_type)

        if not env_key:
            return None

        value = os.getenv(env_key)
        if not value:
            return None

        try:
            return int(value)
        except ValueError:
            return None

    def check_channel_restriction(self, guild_id: int, game_type: str, channel_id: int) -> tuple[bool, str]:
        required_channel_id = self._get_required_channel_id(guild_id, game_type)
        if required_channel_id is None:
            return True, ""

        if channel_id != required_channel_id:
            guild = self.bot.get_guild(guild_id)
            if guild:
                channel = guild.get_channel(required_channel_id)
                target = channel.mention if channel else f"<#{required_channel_id}>"
            else:
                target = f"<#{required_channel_id}>"
            return False, f"❌ 이 게임은 {target} 채널에서만 플레이할 수 있습니다. 올바른 채널에서 다시 시도해 주세요."

        return True, ""

    async def validate_game_start(self, interaction: discord.Interaction, game_type: str, bet: int, min_bet: int = 1, max_bet: int = 10000) -> tuple[bool, str]:
        if not interaction.guild:
            return False, "이 명령은 서버에서만 사용할 수 있습니다."

        if bet < min_bet or bet > max_bet:
            return False, f"베팅은 {min_bet}~{max_bet:,} 코인 사이여야 합니다."

        allowed, channel_message = self.check_channel_restriction(interaction.guild.id, game_type, interaction.channel.id)
        if not allowed:
            return False, channel_message

        coins_cog = self.bot.get_cog("CoinsCog")
        if not coins_cog:
            return False, "코인 시스템을 찾을 수 없습니다."

        user_balance = await coins_cog.get_user_coins(interaction.user.id, interaction.guild.id)
        if user_balance < bet:
            return False, f"코인이 부족합니다. 필요: {bet:,}, 보유: {user_balance:,}"

        return True, ""

    @app_commands.command(name="카지노도움", description="카지노 게임 도움말을 보여줍니다.")
    async def casino_help(self, interaction: discord.Interaction) -> None:
        embed = discord.Embed(
            title="🎰 카지노 게임",
            description="현재 제공되는 게임:\n- `/동전던지기`",
            color=discord.Color.blue(),
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(CasinoBaseCog(bot))
