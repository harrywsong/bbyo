import asyncio
import random

import discord
from discord import app_commands
from discord.ext import commands


class RouletteChoiceView(discord.ui.View):
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

        await coins_cog.remove_coins(interaction.user.id, interaction.guild.id, self.bet, "roulette_bet", "Roulette bet")

        wheel_frames = [
            "🎡 룰렛이 빙글빙글...",
            "🎡 거의 멈추고 있어요...",
            "🎡 마지막 회전!",
        ]
        for frame in wheel_frames:
            embed = discord.Embed(title="🎡 룰렛", description=frame, color=discord.Color.purple())
            embed.add_field(name="🎯 선택", value=self._choice_label(choice), inline=False)
            embed.add_field(name="💳 베팅", value=f"{self.bet:,} 코인", inline=True)
            await interaction.edit_original_response(embed=embed, view=None)
            await asyncio.sleep(0.7)

        number = random.randint(0, 36)
        if number == 0:
            color = "green"
        elif number % 2 == 0:
            color = "black"
        else:
            color = "red"

        won = choice == color
        if won:
            payout = self.bet * 2 if color != "green" else self.bet * 14
            await coins_cog.add_coins(interaction.user.id, interaction.guild.id, payout, "roulette_win", "Roulette win")
            title = "🎉 룰렛 승리!"
            color_code = discord.Color.green()
            result_text = f"{number}번이 나왔고, {self._color_emoji(color)} {color} 색상이었습니다. {payout:,} 코인 지급"
        else:
            title = "😞 룰렛 패배"
            color_code = discord.Color.red()
            result_text = f"{number}번이 나왔고, {self._color_emoji(color)} {color} 색상이었습니다."

        final_embed = discord.Embed(title=title, color=color_code)
        final_embed.add_field(name="🎯 결과", value=result_text, inline=False)
        final_embed.add_field(name="💳 베팅", value=f"{self.bet:,} 코인", inline=True)
        final_embed.add_field(name="🏦 잔액", value=f"{await coins_cog.get_user_coins(interaction.user.id, interaction.guild.id):,} 코인", inline=True)
        await interaction.edit_original_response(embed=final_embed, view=None)

    def _choice_label(self, choice: str) -> str:
        return {"red": "🔴 빨강", "black": "⚫ 검정", "green": "🟢 초록"}.get(choice, choice)

    def _color_emoji(self, color: str) -> str:
        return {"red": "🔴", "black": "⚫", "green": "🟢"}.get(color, "⚪")

    @discord.ui.button(label="🔴 빨강", style=discord.ButtonStyle.red)
    async def red_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await self._play(interaction, "red")

    @discord.ui.button(label="⚫ 검정", style=discord.ButtonStyle.secondary)
    async def black_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await self._play(interaction, "black")

    @discord.ui.button(label="🟢 초록", style=discord.ButtonStyle.green)
    async def green_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await self._play(interaction, "green")


class RouletteCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def _validate(self, interaction: discord.Interaction, bet: int) -> tuple[bool, str]:
        casino_base = self.bot.get_cog("CasinoBaseCog")
        if not casino_base:
            return False, "카지노 시스템을 찾을 수 없습니다."
        return await casino_base.validate_game_start(interaction, "roulette", bet, min_bet=1, max_bet=10000)

    @app_commands.command(name="룰렛", description="룰렛에서 색상을 맞춥니다.")
    @app_commands.describe(bet="베팅 코인")
    async def roulette(self, interaction: discord.Interaction, bet: int) -> None:
        if not interaction.guild:
            await interaction.response.send_message("이 명령은 서버에서만 사용할 수 있습니다.", ephemeral=True)
            return

        can_start, error = await self._validate(interaction, bet)
        if not can_start:
            await interaction.response.send_message(error, ephemeral=True)
            return

        embed = discord.Embed(title="🎡 룰렛", description="색상을 선택해 주세요.", color=discord.Color.purple())
        embed.add_field(name="💳 베팅", value=f"{bet:,} 코인", inline=False)
        await interaction.response.send_message(embed=embed, view=RouletteChoiceView(self.bot, interaction, bet))


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(RouletteCog(bot))
