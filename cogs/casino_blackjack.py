import random

import discord
from discord import app_commands
from discord.ext import commands


SUIT_EMOJIS = ["♠️", "♥️", "♦️", "♣️"]


class BlackjackView(discord.ui.View):
    def __init__(self, bot: commands.Bot, interaction: discord.Interaction, bet: int, player_hand: list[tuple[int, str]], dealer_hand: list[tuple[int, str]], coins_cog) -> None:
        super().__init__(timeout=120)
        self.bot = bot
        self.interaction = interaction
        self.bet = bet
        self.dealer_hand = dealer_hand
        self.coins_cog = coins_cog
        self.finished = False
        self.player_hands = [player_hand]
        self.hand_bets = [bet]
        self.current_hand_index = 0

    def _draw_card(self) -> tuple[int, str]:
        rank = random.choice([2, 3, 4, 5, 6, 7, 8, 9, 10, 10, 10, 10, 11])
        suit = random.choice(SUIT_EMOJIS)
        return rank, suit

    def _hand_total(self, hand: list[tuple[int, str]]) -> int:
        values = [card[0] for card in hand]
        total = sum(values)
        while total > 21 and 11 in values:
            values.remove(11)
            values.append(1)
            total = sum(values)
        return total

    def _current_hand(self) -> list[tuple[int, str]]:
        return self.player_hands[self.current_hand_index]

    def _current_bet(self) -> int:
        return self.hand_bets[self.current_hand_index]

    def _format_hand(self, hand: list[tuple[int, str]]) -> str:
        return " ".join(f"{rank}{suit}" for rank, suit in hand)

    async def _refresh_button_states(self) -> None:
        if self.finished:
            for child in self.children:
                child.disabled = True
            return

        current_hand = self._current_hand()
        current_total = self._hand_total(current_hand)
        balance = await self.coins_cog.get_user_coins(self.interaction.user.id, self.interaction.guild.id)

        self.hit_button.disabled = current_total >= 21
        self.stand_button.disabled = False
        self.double_button.disabled = not (len(current_hand) == 2 and current_total in {9, 10, 11} and balance >= self._current_bet() + self.bet)
        self.split_button.disabled = not (len(current_hand) == 2 and current_hand[0][0] == current_hand[1][0] and balance >= self._current_bet() + self.bet)

    async def _show_state(self, interaction: discord.Interaction, title: str, description: str, color: discord.Color) -> None:
        await self._refresh_button_states()
        embed = discord.Embed(title=title, description=description, color=color)
        embed.add_field(name="🃏 현재 손", value=f"{self._format_hand(self._current_hand())}  (총합 {self._hand_total(self._current_hand())})", inline=False)
        embed.add_field(name="🂠 딜러", value=f"{self._format_hand(self.dealer_hand)}  (총합 {self._hand_total(self.dealer_hand)})", inline=True)
        embed.add_field(name="💳 베팅", value=f"{self._current_bet():,} 코인", inline=True)
        await interaction.response.edit_message(embed=embed, view=self)

    async def _advance_hand(self, interaction: discord.Interaction) -> None:
        self.current_hand_index += 1
        if self.current_hand_index >= len(self.player_hands):
            await self._resolve_game(interaction)
            return

        await self._show_state(interaction, "🃏 블랙잭", "다음 손으로 넘어갑니다.", discord.Color.blue())

    async def _resolve_game(self, interaction: discord.Interaction) -> None:
        self.finished = True
        for child in self.children:
            child.disabled = True

        dealer_total = self._hand_total(self.dealer_hand)
        while dealer_total < 17:
            self.dealer_hand.append(self._draw_card())
            dealer_total = self._hand_total(self.dealer_hand)

        result_lines = []
        for index, (hand, hand_bet) in enumerate(zip(self.player_hands, self.hand_bets), start=1):
            player_total = self._hand_total(hand)
            if player_total > 21:
                result_lines.append(f"손 {index}: Bust")
            elif dealer_total > 21 or player_total > dealer_total:
                payout = hand_bet * 2
                await self.coins_cog.add_coins(interaction.user.id, interaction.guild.id, payout, "blackjack_win", "Blackjack win")
                result_lines.append(f"손 {index}: 승리 (+{payout:,})")
            elif player_total < dealer_total:
                result_lines.append(f"손 {index}: 패배")
            else:
                await self.coins_cog.add_coins(interaction.user.id, interaction.guild.id, hand_bet, "blackjack_push", "Blackjack push")
                result_lines.append(f"손 {index}: 무승부")

        embed = discord.Embed(title="🃏 블랙잭 결과", color=discord.Color.gold())
        embed.add_field(name="🂠 딜러", value=f"{self._format_hand(self.dealer_hand)}  (총합 {dealer_total})", inline=False)
        embed.add_field(name="📊 결과", value="\n".join(result_lines), inline=False)
        embed.add_field(name="🏦 잔액", value=f"{await self.coins_cog.get_user_coins(interaction.user.id, interaction.guild.id):,} 코인", inline=False)
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="🎯 히트", style=discord.ButtonStyle.green)
    async def hit_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if self.finished:
            return
        self._current_hand().append(self._draw_card())
        if self._hand_total(self._current_hand()) > 21:
            await self._advance_hand(interaction)
            return
        await self._show_state(interaction, "🃏 블랙잭", "카드를 한 장 더 받았습니다.", discord.Color.blue())

    @discord.ui.button(label="🛑 스탠드", style=discord.ButtonStyle.red)
    async def stand_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if self.finished:
            return
        await self._advance_hand(interaction)

    @discord.ui.button(label="➕ 더블", style=discord.ButtonStyle.blurple)
    async def double_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if self.finished:
            return
        balance = await self.coins_cog.get_user_coins(interaction.user.id, interaction.guild.id)
        if balance < self._current_bet() + self.bet:
            await self._show_state(interaction, "🃏 블랙잭", "더블다운에 필요한 코인이 부족합니다.", discord.Color.red())
            return

        await self.coins_cog.remove_coins(interaction.user.id, interaction.guild.id, self.bet, "blackjack_double", "Blackjack double")
        self._current_hand().append(self._draw_card())
        self.hand_bets[self.current_hand_index] += self.bet
        await self._advance_hand(interaction)

    @discord.ui.button(label="✂️ 스플릿", style=discord.ButtonStyle.secondary)
    async def split_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if self.finished:
            return
        balance = await self.coins_cog.get_user_coins(interaction.user.id, interaction.guild.id)
        if balance < self._current_bet() + self.bet:
            await self._show_state(interaction, "🃏 블랙잭", "스플릿에 필요한 코인이 부족합니다.", discord.Color.red())
            return

        current_hand = self._current_hand()
        if len(current_hand) != 2 or current_hand[0][0] != current_hand[1][0]:
            await self._show_state(interaction, "🃏 블랙잭", "스플릿은 시작 손의 같은 숫자 두 장일 때만 가능합니다.", discord.Color.red())
            return

        await self.coins_cog.remove_coins(interaction.user.id, interaction.guild.id, self.bet, "blackjack_split", "Blackjack split")
        first_card = current_hand[0]
        second_card = current_hand[1]
        self.player_hands[self.current_hand_index] = [first_card]
        self.player_hands.insert(self.current_hand_index + 1, [second_card])
        self.hand_bets[self.current_hand_index] = self.bet
        self.hand_bets.insert(self.current_hand_index + 1, self.bet)
        self._current_hand().append(self._draw_card())
        self.player_hands[self.current_hand_index + 1].append(self._draw_card())
        await self._show_state(interaction, "🃏 블랙잭", "핸드가 나뉘었습니다. 각 손에 대해 행동을 선택하세요.", discord.Color.orange())


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

        player_hand = [
            (random.choice([2, 3, 4, 5, 6, 7, 8, 9, 10, 10, 10, 10, 11]), random.choice(SUIT_EMOJIS)),
            (random.choice([2, 3, 4, 5, 6, 7, 8, 9, 10, 10, 10, 10, 11]), random.choice(SUIT_EMOJIS)),
        ]
        dealer_hand = [
            (random.choice([2, 3, 4, 5, 6, 7, 8, 9, 10, 10, 10, 10, 11]), random.choice(SUIT_EMOJIS)),
        ]

        view = BlackjackView(self.bot, interaction, bet, player_hand, dealer_hand, coins_cog)
        await view._refresh_button_states()

        embed = discord.Embed(title="🃏 블랙잭", description="히트, 스탠드, 더블다운 또는 스플릿을 선택하세요.", color=discord.Color.blue())
        embed.add_field(name="🃏 플레이어", value=f"{view._format_hand(view._current_hand())}  (총합 {view._hand_total(view._current_hand())})", inline=True)
        embed.add_field(name="🂠 딜러", value=f"{view._format_hand(dealer_hand)}  (총합 {view._hand_total(dealer_hand)})", inline=True)
        embed.add_field(name="💳 베팅", value=f"{bet:,} 코인", inline=True)
        await interaction.response.send_message(embed=embed, view=view)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(BlackjackCog(bot))
