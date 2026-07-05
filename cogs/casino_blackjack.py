import random

import discord
from discord import app_commands
from discord.ext import commands


class BlackjackView(discord.ui.View):
    def __init__(self, bot: commands.Bot, interaction: discord.Interaction, bet: int, player_hand: list[int], dealer_hand: list[int], coins_cog) -> None:
        super().__init__(timeout=120)
        self.bot = bot
        self.interaction = interaction
        self.bet = bet
        self.player_hand = player_hand
        self.dealer_hand = dealer_hand
        self.coins_cog = coins_cog
        self.finished = False

    def _draw_card(self) -> int:
        return random.choice([2, 3, 4, 5, 6, 7, 8, 9, 10, 10, 10, 10, 11])

    def _hand_total(self, hand: list[int]) -> int:
        total = sum(hand)
        while total > 21 and 11 in hand:
            hand.remove(11)
            hand.append(1)
            total = sum(hand)
        return total

    def _build_embed(self, title: str, color: discord.Color, description: str) -> discord.Embed:
        embed = discord.Embed(title=title, description=description, color=color)
        embed.add_field(name="🃏 플레이어", value=f"총합 {self._hand_total(self.player_hand)}", inline=True)
        embed.add_field(name="🂠 딜러", value=f"총합 {self._hand_total(self.dealer_hand)}", inline=True)
        embed.add_field(name="💳 베팅", value=f"{self.bet:,} 코인", inline=True)
        return embed

    async def _resolve(self, interaction: discord.Interaction, title: str, color: discord.Color, description: str, payout: int) -> None:
        self.finished = True
        for child in self.children:
            child.disabled = True
        if payout > 0:
            await self.coins_cog.add_coins(interaction.user.id, interaction.guild.id, payout, "blackjack_win", "Blackjack win")
        elif payout == 0 and title != "🤝 블랙잭 무승부":
            pass
        elif payout == self.bet:
            await self.coins_cog.add_coins(interaction.user.id, interaction.guild.id, payout, "blackjack_push", "Blackjack push")

        embed = self._build_embed(title, color, description)
        embed.add_field(name="📊 결과", value=description, inline=False)
        embed.add_field(name="🏦 잔액", value=f"{await self.coins_cog.get_user_coins(interaction.user.id, interaction.guild.id):,} 코인", inline=False)
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="🎯 히트", style=discord.ButtonStyle.green)
    async def hit_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if self.finished:
            return
        self.player_hand.append(self._draw_card())
        player_total = self._hand_total(self.player_hand)
        if player_total > 21:
            await self._resolve(interaction, "😞 블랙잭 패배", discord.Color.red(), "플레이어가 bust 되어 패배했습니다.", 0)
            return

        embed = self._build_embed("🃏 블랙잭", discord.Color.blue(), "카드를 한 장 더 받았습니다.")
        embed.add_field(name="📌 다음 행동", value="히트하거나 스탠드하세요.", inline=False)
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="🛑 스탠드", style=discord.ButtonStyle.red)
    async def stand_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if self.finished:
            return
        dealer_total = self._hand_total(self.dealer_hand)
        while dealer_total < 17:
            self.dealer_hand.append(self._draw_card())
            dealer_total = self._hand_total(self.dealer_hand)

        player_total = self._hand_total(self.player_hand)
        if dealer_total > 21 or player_total > dealer_total:
            await self._resolve(interaction, "🎉 블랙잭 승리!", discord.Color.green(), f"플레이어 {player_total} : 딜러 {dealer_total}", self.bet * 2)
        elif player_total < dealer_total:
            await self._resolve(interaction, "😞 블랙잭 패배", discord.Color.red(), f"플레이어 {player_total} : 딜러 {dealer_total}", 0)
        else:
            await self._resolve(interaction, "🤝 블랙잭 무승부", discord.Color.orange(), f"무승부! 플레이어 {player_total} : 딜러 {dealer_total}", self.bet)


class BlackjackCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def _validate(self, interaction: discord.Interaction, bet: int) -> tuple[bool, str]:
        casino_base = self.bot.get_cog("CasinoBaseCog")
        if not casino_base:
            return False, "카지노 시스템을 찾을 수 없습니다."
        return await casino_base.validate_game_start(interaction, "blackjack", bet, min_bet=1, max_bet=10000)

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

        await coins_cog.remove_coins(interaction.user.id, interaction.guild.id, bet, "blackjack_bet", "Blackjack bet")

        player_hand = [random.choice([2, 3, 4, 5, 6, 7, 8, 9, 10, 10, 10, 10, 11]), random.choice([2, 3, 4, 5, 6, 7, 8, 9, 10, 10, 10, 10, 11])]
        dealer_hand = [random.choice([2, 3, 4, 5, 6, 7, 8, 9, 10, 10, 10, 10, 11])]

        embed = discord.Embed(title="🃏 블랙잭", description="히트 또는 스탠드로 진행하세요.", color=discord.Color.blue())
        embed.add_field(name="🃏 플레이어", value=f"총합 {sum(player_hand)}", inline=True)
        embed.add_field(name="🂠 딜러", value=f"총합 {sum(dealer_hand)}", inline=True)
        embed.add_field(name="💳 베팅", value=f"{bet:,} 코인", inline=True)
        await interaction.response.send_message(embed=embed, view=BlackjackView(self.bot, interaction, bet, player_hand, dealer_hand, coins_cog))


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(BlackjackCog(bot))
