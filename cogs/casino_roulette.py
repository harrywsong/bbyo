import random

import discord
from discord.ext import commands
from discord import app_commands


class RouletteCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def _validate(self, interaction: discord.Interaction, bet: int) -> tuple[bool, str]:
        casino_base = self.bot.get_cog("CasinoBaseCog")
        if not casino_base:
            return False, "카지노 시스템을 찾을 수 없습니다."
        return await casino_base.validate_game_start(interaction, "roulette", bet, min_bet=1, max_bet=10000)

    @app_commands.command(name="룰렛", description="룰렛에서 색상을 맞춥니다.")
    @app_commands.describe(bet="베팅 코인", choice="red, black, green")
    @app_commands.choices(choice=[
        app_commands.Choice(name="🔴 빨강", value="red"),
        app_commands.Choice(name="⚫ 검정", value="black"),
        app_commands.Choice(name="🟢 초록", value="green"),
    ])
    async def roulette(self, interaction: discord.Interaction, bet: int, choice: str) -> None:
        if not interaction.guild:
            await interaction.response.send_message("이 명령은 서버에서만 사용할 수 있습니다.", ephemeral=True)
            return

        can_start, error = await self._validate(interaction, bet)
        if not can_start:
            await interaction.response.send_message(error, ephemeral=True)
            return

        coins_cog = self.bot.get_cog("CoinsCog")
        if not coins_cog:
            await interaction.response.send_message("코인 시스템을 찾을 수 없습니다.", ephemeral=True)
            return

        await interaction.response.defer(thinking=True)
        await coins_cog.remove_coins(interaction.user.id, interaction.guild.id, bet, "roulette_bet", "Roulette bet")

        number = random.randint(0, 36)
        if number == 0:
            color = "green"
        elif number % 2 == 0:
            color = "black"
        else:
            color = "red"

        won = choice == color
        if won:
            payout = bet * 2 if color != "green" else bet * 14
            await coins_cog.add_coins(interaction.user.id, interaction.guild.id, payout, "roulette_win", "Roulette win")
            title = "🎉 룰렛 승리!"
            color_code = discord.Color.green()
            result_text = f"{number}번이 나왔고, {color} 색상이었습니다. {payout:,} 코인 지급"
        else:
            title = "😞 룰렛 패배"
            color_code = discord.Color.red()
            result_text = f"{number}번이 나왔고, {color} 색상이었습니다."

        embed = discord.Embed(title=title, color=color_code)
        embed.add_field(name="🎯 결과", value=result_text, inline=False)
        embed.add_field(name="💳 베팅", value=f"{bet:,} 코인", inline=True)
        embed.add_field(name="🏦 잔액", value=f"{await coins_cog.get_user_coins(interaction.user.id, interaction.guild.id):,} 코인", inline=True)
        await interaction.followup.send(embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(RouletteCog(bot))
