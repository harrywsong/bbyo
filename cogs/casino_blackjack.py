import random

import discord
from discord.ext import commands
from discord import app_commands


class BlackjackCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def _validate(self, interaction: discord.Interaction, bet: int) -> tuple[bool, str]:
        casino_base = self.bot.get_cog("CasinoBaseCog")
        if not casino_base:
            return False, "카지노 시스템을 찾을 수 없습니다."
        return await casino_base.validate_game_start(interaction, "blackjack", bet, min_bet=1, max_bet=10000)

    def _draw_card(self) -> tuple[int, str]:
        ranks = [2, 3, 4, 5, 6, 7, 8, 9, 10, 10, 10, 10, 11]
        rank = random.choice(ranks)
        suit = random.choice(["♠", "♥", "♦", "♣"])
        return rank, suit

    def _hand_total(self, hand: list[int]) -> int:
        total = sum(hand)
        while total > 21 and 11 in hand:
            hand.remove(11)
            hand.append(1)
            total = sum(hand)
        return total

    @app_commands.command(name="블랙잭", description="간단한 블랙잭 한 판을 플레이합니다.")
    @app_commands.describe(bet="베팅 코인")
    async def blackjack(self, interaction: discord.Interaction, bet: int) -> None:
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
        await coins_cog.remove_coins(interaction.user.id, interaction.guild.id, bet, "blackjack_bet", "Blackjack bet")

        player_hand = []
        dealer_hand = []
        for _ in range(2):
            value, suit = self._draw_card()
            player_hand.append(value)
            value, suit = self._draw_card()
            dealer_hand.append(value)

        player_total = self._hand_total(player_hand)
        dealer_total = self._hand_total(dealer_hand)

        while dealer_total < 17:
            value, suit = self._draw_card()
            dealer_hand.append(value)
            dealer_total = self._hand_total(dealer_hand)

        if player_total > 21:
            result_text = "플레이어가 bust 되어 패배했습니다."
            title = "😞 블랙잭 패배"
            color = discord.Color.red()
            payout = 0
        elif dealer_total > 21:
            payout = bet * 2
            await coins_cog.add_coins(interaction.user.id, interaction.guild.id, payout, "blackjack_win", "Blackjack win")
            result_text = "딜러가 bust 되어 승리했습니다."
            title = "🎉 블랙잭 승리!"
            color = discord.Color.green()
        elif player_total > dealer_total:
            payout = bet * 2
            await coins_cog.add_coins(interaction.user.id, interaction.guild.id, payout, "blackjack_win", "Blackjack win")
            result_text = f"플레이어 {player_total} : 딜러 {dealer_total}"
            title = "🎉 블랙잭 승리!"
            color = discord.Color.green()
        elif player_total < dealer_total:
            result_text = f"플레이어 {player_total} : 딜러 {dealer_total}"
            title = "😞 블랙잭 패배"
            color = discord.Color.red()
            payout = 0
        else:
            payout = bet
            await coins_cog.add_coins(interaction.user.id, interaction.guild.id, payout, "blackjack_push", "Blackjack push")
            result_text = f"무승부! 플레이어 {player_total} : 딜러 {dealer_total}"
            title = "🤝 블랙잭 무승부"
            color = discord.Color.orange()

        embed = discord.Embed(title=title, color=color)
        embed.add_field(name="🃏 플레이어", value=f"총합 {player_total}", inline=True)
        embed.add_field(name="🂠 딜러", value=f"총합 {dealer_total}", inline=True)
        embed.add_field(name="💳 베팅", value=f"{bet:,} 코인", inline=True)
        embed.add_field(name="📊 결과", value=result_text, inline=False)
        embed.add_field(name="🏦 잔액", value=f"{await coins_cog.get_user_coins(interaction.user.id, interaction.guild.id):,} 코인", inline=False)
        await interaction.followup.send(embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(BlackjackCog(bot))
