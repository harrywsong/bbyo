import os

import discord
from discord.ext import commands


class CoinGrantModal(discord.ui.Modal, title="코인 지급"):
    user = discord.ui.TextInput(label="유저 ID", placeholder="숫자만 입력", required=True)
    amount = discord.ui.TextInput(label="지급할 코인 수", placeholder="예: 100", required=True)

    def __init__(self, bot: commands.Bot) -> None:
        super().__init__()
        self.bot = bot

    async def on_submit(self, interaction: discord.Interaction) -> None:
        try:
            target_user_id = int(self.user.value)
            amount = int(self.amount.value)
        except ValueError:
            await interaction.response.send_message("유저 ID와 코인 수는 숫자여야 합니다.", ephemeral=True)
            return

        if amount <= 0:
            await interaction.response.send_message("지급할 코인 수는 1 이상이어야 합니다.", ephemeral=True)
            return

        coins_cog = self.bot.get_cog("CoinsCog")
        if not coins_cog:
            await interaction.response.send_message("코인 시스템을 찾을 수 없습니다.", ephemeral=True)
            return

        await coins_cog.add_coins(target_user_id, interaction.guild.id, amount, "admin_grant", "Admin test grant")
        await interaction.response.send_message(f"{target_user_id}에게 {amount:,} 코인을 지급했습니다.", ephemeral=True)


class CoinGrantView(discord.ui.View):
    def __init__(self, bot: commands.Bot) -> None:
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(label="💰 코인 지급", style=discord.ButtonStyle.green, custom_id="persistent_coin_grant")
    async def coin_grant(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if not interaction.guild:
            await interaction.response.send_message("이 명령은 서버에서만 사용할 수 있습니다.", ephemeral=True)
            return

        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("관리자만 사용할 수 있습니다.", ephemeral=True)
            return

        await interaction.response.send_modal(CoinGrantModal(self.bot))


class AdminTestToolsCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.channel_id = int(os.getenv("CASINO_TEST_CHANNEL_ID", "0")) if os.getenv("CASINO_TEST_CHANNEL_ID") else None
        self.panel_message_id = None

    async def ensure_panel(self) -> None:
        if not self.channel_id:
            return

        channel = self.bot.get_channel(self.channel_id)
        if not channel or not hasattr(channel, "send"):
            return

        if self.panel_message_id:
            try:
                message = await channel.fetch_message(self.panel_message_id)
                await message.edit(view=CoinGrantView(self.bot))
                return
            except discord.NotFound:
                self.panel_message_id = None

        async for message in channel.history(limit=50):
            if message.author == self.bot.user and message.embeds and "테스트 패널" in message.embeds[0].title:
                self.panel_message_id = message.id
                await message.edit(view=CoinGrantView(self.bot))
                return

        embed = discord.Embed(title="🧪 테스트 패널", description="아래 버튼을 눌러 코인을 지급할 수 있습니다.", color=discord.Color.orange())
        message = await channel.send(embed=embed, view=CoinGrantView(self.bot))
        self.panel_message_id = message.id

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        await self.ensure_panel()


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(AdminTestToolsCog(bot))
