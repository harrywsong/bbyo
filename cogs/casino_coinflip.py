import asyncio
import random

import discord
from discord import app_commands
from discord.ext import commands


class CoinflipChoiceView(discord.ui.View):
    def __init__(self, bot: commands.Bot, interaction: discord.Interaction, bet: int) -> None:
        super().__init__(timeout=60)
        self.bot = bot
        self.interaction = interaction
        self.bet = bet

    async def _play(self, interaction: discord.Interaction, choice: str) -> None:
        await interaction.response.defer()
        coins_cog = self.bot.get_cog("CoinsCog")
        if not coins_cog:
            await interaction.edit_original_response(content="코인 시스템을 찾을 수 없습니다.")
            return

        await coins_cog.remove_coins(interaction.user.id, interaction.guild.id, self.bet, "coinflip_bet", "Coinflip bet")

        frames = [
            "🪙 **동전이 공중에서 빙글빙글...**",
            "🪙 **한 바퀴 더...**",
            "🪙 **거의 끝났어요!**",
            "🪙 **착지하는 중...**",
        ]

        for frame in frames:
            embed = discord.Embed(title="🪙 동전던지기", description=frame, color=discord.Color.blurple())
            embed.add_field(name="🎯 선택", value="👑 앞면" if choice == "heads" else "⚫ 뒷면", inline=False)
            embed.add_field(name="💳 베팅", value=f"{self.bet:,} 코인", inline=True)
            await interaction.edit_original_response(embed=embed, view=None)
            await asyncio.sleep(0.6)

        result = random.choice(["heads", "tails"])
        won = result == choice
        payout = self.bet * 2 if won else 0

        if won:
            await coins_cog.add_coins(interaction.user.id, interaction.guild.id, payout, "coinflip_win", "Coinflip win")

        final_embed = discord.Embed(title="🪙 동전던지기", color=discord.Color.green() if won else discord.Color.red())
        final_embed.add_field(name="🎯 결과", value=f"{'👑 앞면' if result == 'heads' else '⚫ 뒷면'}", inline=False)
        final_embed.add_field(name="💳 베팅", value=f"{self.bet:,} 코인", inline=True)
        final_embed.add_field(name="📊 결과", value="✅ 적중!" if won else "❌ 빗나감!", inline=True)
        final_embed.add_field(name="🏦 잔액", value=f"{await coins_cog.get_user_coins(interaction.user.id, interaction.guild.id):,} 코인", inline=False)
        await interaction.edit_original_response(embed=final_embed, view=None)

    @discord.ui.button(label="👑 앞면", style=discord.ButtonStyle.blurple)
    async def heads_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await self._play(interaction, "heads")

    @discord.ui.button(label="⚫ 뒷면", style=discord.ButtonStyle.secondary)
    async def tails_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await self._play(interaction, "tails")


class CoinflipCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def _validate(self, interaction: discord.Interaction, bet: int) -> tuple[bool, str]:
        casino_base = self.bot.get_cog("CasinoBaseCog")
        if not casino_base:
            return False, "카지노 시스템을 찾을 수 없습니다."
        return await casino_base.validate_game_start(interaction, "coinflip", bet, min_bet=1, max_bet=5000)

    @app_commands.command(name="동전던지기", description="동전을 던져 앞면/뒷면을 맞춥니다.")
    @app_commands.describe(bet="베팅 코인")
    async def coinflip(self, interaction: discord.Interaction, bet: int) -> None:
        if not interaction.guild:
            await interaction.response.send_message("이 명령은 서버에서만 사용할 수 있습니다.", ephemeral=True)
            return

        can_start, error = await self._validate(interaction, bet)
        if not can_start:
            await interaction.response.send_message(error, ephemeral=True)
            return

        embed = discord.Embed(title="🪙 동전던지기", description="앞면 또는 뒷면을 선택해 주세요.", color=discord.Color.blurple())
        embed.add_field(name="💳 베팅", value=f"{bet:,} 코인", inline=False)
        embed.set_footer(text="버튼을 눌러 결과를 확인하세요.")
        await interaction.response.send_message(embed=embed, view=CoinflipChoiceView(self.bot, interaction, bet))


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(CoinflipCog(bot))
