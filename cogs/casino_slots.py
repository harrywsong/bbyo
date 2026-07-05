import asyncio
import random

import discord
from discord import app_commands
from discord.ext import commands


class SlotsSpinView(discord.ui.View):
    def __init__(self, bot: commands.Bot, interaction: discord.Interaction, bet: int) -> None:
        super().__init__(timeout=60)
        self.bot = bot
        self.interaction = interaction
        self.bet = bet

    @discord.ui.button(label="🎰 돌리기", style=discord.ButtonStyle.green)
    async def spin(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await interaction.response.defer()
        coins_cog = self.bot.get_cog("CoinsCog")
        if not coins_cog:
            await interaction.edit_original_response(content="코인 시스템을 찾을 수 없습니다.")
            return

        await coins_cog.remove_coins(interaction.user.id, interaction.guild.id, self.bet, "slot_bet", "Slots bet")
        symbols = ["🍒", "🍋", "⭐", "🔔", "💎", "7️⃣"]

        for _ in range(4):
            reels = [random.choice(symbols) for _ in range(3)]
            embed = discord.Embed(title="🎰 슬롯머신", description="🔄 회전 중...", color=discord.Color.gold())
            embed.add_field(name="🎲 결과", value=" | ".join(reels), inline=False)
            embed.add_field(name="💳 베팅", value=f"{self.bet:,} 코인", inline=True)
            await interaction.edit_original_response(embed=embed, view=None)
            await asyncio.sleep(0.5)

        reels = [random.choice(symbols) for _ in range(3)]
        result = " | ".join(reels)
        if reels[0] == reels[1] == reels[2]:
            if reels[0] == "7️⃣":
                payout = self.bet * 20
                outcome = f"🎉 잭팟! {payout:,} 코인 지급"
                color = discord.Color.gold()
            else:
                payout = self.bet * 10
                outcome = f"🎉 10배 당첨! {payout:,} 코인 지급"
                color = discord.Color.green()
            await coins_cog.add_coins(interaction.user.id, interaction.guild.id, payout, "slot_win", "Slots win")
        elif reels[0] == reels[1] or reels[1] == reels[2] or reels[0] == reels[2]:
            payout = self.bet * 2
            await coins_cog.add_coins(interaction.user.id, interaction.guild.id, payout, "slot_win", "Slots win")
            outcome = f"✨ 2배 보너스! {payout:,} 코인 지급"
            color = discord.Color.blue()
        else:
            outcome = "😞 패배! 다음 기회에 도전해 보세요."
            color = discord.Color.red()

        final_embed = discord.Embed(title="🎰 슬롯머신", color=color)
        final_embed.add_field(name="🎲 결과", value=result, inline=False)
        final_embed.add_field(name="💳 베팅", value=f"{self.bet:,} 코인", inline=True)
        final_embed.add_field(name="📊 결과", value=outcome, inline=True)
        final_embed.set_footer(text=f"잔액: {await coins_cog.get_user_coins(interaction.user.id, interaction.guild.id):,} 코인")
        await interaction.edit_original_response(embed=final_embed, view=None)


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

        embed = discord.Embed(title="🎰 슬롯머신", description="버튼을 눌러 슬롯을 돌려 보세요.", color=discord.Color.gold())
        embed.add_field(name="💳 베팅", value=f"{bet:,} 코인", inline=False)
        await interaction.response.send_message(embed=embed, view=SlotsSpinView(self.bot, interaction, bet))


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(SlotsCog(bot))
