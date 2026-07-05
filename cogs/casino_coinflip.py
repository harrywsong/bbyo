import asyncio
import random

import discord
from discord.ext import commands
from discord import app_commands


class CoinflipCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def _validate(self, interaction: discord.Interaction, bet: int) -> tuple[bool, str]:
        casino_base = self.bot.get_cog("CasinoBaseCog")
        if not casino_base:
            return False, "카지노 시스템을 찾을 수 없습니다."
        return await casino_base.validate_game_start(interaction, "coinflip", bet, min_bet=1, max_bet=5000)

    @app_commands.command(name="동전던지기", description="동전을 던져 앞면/뒷면을 맞춥니다.")
    @app_commands.describe(bet="베팅 코인", choice="앞면 또는 뒷면")
    @app_commands.choices(choice=[
        app_commands.Choice(name="👑 앞면", value="heads"),
        app_commands.Choice(name="⚫ 뒷면", value="tails"),
    ])
    async def coinflip(self, interaction: discord.Interaction, bet: int, choice: str) -> None:
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

        await self._deduct_bet(coins_cog, interaction, bet)

        result = random.choice(["heads", "tails"])
        won = result == choice
        payout = bet * 2 if won else 0

        if won:
            await coins_cog.add_coins(interaction.user.id, interaction.guild.id, payout, "coinflip_win", "Coinflip win")

        embed = discord.Embed(title="🪙 동전던지기", color=discord.Color.green() if won else discord.Color.red())
        embed.add_field(name="🎯 결과", value=f"{result}", inline=False)
        embed.add_field(name="💳 베팅", value=f"{bet:,} 코인", inline=True)
        embed.add_field(name="🏦 잔액", value=f"{await coins_cog.get_user_coins(interaction.user.id, interaction.guild.id):,} 코인", inline=True)
        await interaction.followup.send(embed=embed)

    async def _deduct_bet(self, coins_cog, interaction: discord.Interaction, bet: int) -> None:
        await coins_cog.remove_coins(interaction.user.id, interaction.guild.id, bet, "coinflip_bet", "Coinflip bet")


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(CoinflipCog(bot))
