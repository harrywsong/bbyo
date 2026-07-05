import discord
from discord.ext import commands
from discord import app_commands


class CasinoBaseCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def validate_game_start(self, interaction: discord.Interaction, game_type: str, bet: int, min_bet: int = 1, max_bet: int = 10000) -> tuple[bool, str]:
        if not interaction.guild:
            return False, "이 명령은 서버에서만 사용할 수 있습니다."

        if bet < min_bet or bet > max_bet:
            return False, f"베팅은 {min_bet}~{max_bet:,} 코인 사이여야 합니다."

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
