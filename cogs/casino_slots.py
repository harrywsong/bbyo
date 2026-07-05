import random

import discord
from discord.ext import commands
from discord import app_commands


class SlotsCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def _validate(self, interaction: discord.Interaction, bet: int) -> tuple[bool, str]:
        casino_base = self.bot.get_cog("CasinoBaseCog")
        if not casino_base:
            return False, "카지노 시스템을 찾을 수 없습니다."
        return await casino_base.validate_game_start(interaction, "slot_machine", bet, min_bet=1, max_bet=10000)

    @app_commands.command(name="슬롯", description="슬롯머신을 돌립니다.")
    @app_commands.describe(bet="베팅 코인")
    async def slots(self, interaction: discord.Interaction, bet: int) -> None:
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
        await coins_cog.remove_coins(interaction.user.id, interaction.guild.id, bet, "slot_bet", "Slots bet")

        symbols = ["🍒", "🍋", "⭐", "🔔", "💎", "7️⃣"]
        reels = [random.choice(symbols) for _ in range(3)]
        result = " | ".join(reels)

        if reels[0] == reels[1] == reels[2]:
            if reels[0] == "7️⃣":
                multiplier = 20
            else:
                multiplier = 10
            payout = bet * multiplier
            await coins_cog.add_coins(interaction.user.id, interaction.guild.id, payout, "slot_win", "Slots win")
            title = "🎉 슬롯 승리!"
            color = discord.Color.gold()
            outcome = f"{multiplier}배 당첨! {payout:,} 코인 지급"
        elif reels[0] == reels[1] or reels[1] == reels[2] or reels[0] == reels[2]:
            multiplier = 2
            payout = bet * multiplier
            await coins_cog.add_coins(interaction.user.id, interaction.guild.id, payout, "slot_win", "Slots win")
            title = "✨ 슬롯 보너스"
            color = discord.Color.blue()
            outcome = f"2배 당첨! {payout:,} 코인 지급"
        else:
            title = "😞 슬롯 패배"
            color = discord.Color.red()
            outcome = "다음 기회에 도전해보세요."

        embed = discord.Embed(title=title, color=color)
        embed.add_field(name="🎰 결과", value=result, inline=False)
        embed.add_field(name="💳 베팅", value=f"{bet:,} 코인", inline=True)
        embed.add_field(name="📊 결과", value=outcome, inline=True)
        embed.set_footer(text=f"잔액: {await coins_cog.get_user_coins(interaction.user.id, interaction.guild.id):,} 코인")
        await interaction.followup.send(embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(SlotsCog(bot))
