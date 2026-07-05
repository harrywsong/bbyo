import json
import os
import sqlite3
from datetime import datetime, timedelta, timezone

import discord
from discord import app_commands
from discord.ext import commands


class CoinsCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self._db_path = os.path.join(os.path.dirname(__file__), "..", "data", "bbyo.db")
        self._ensure_database()
        self._migrate_from_json_if_needed()

    def _ensure_database(self) -> None:
        os.makedirs(os.path.dirname(self._db_path), exist_ok=True)
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS user_balances (
                    guild_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    coins INTEGER NOT NULL DEFAULT 0,
                    last_claim_date TEXT,
                    total_earned INTEGER NOT NULL DEFAULT 0,
                    PRIMARY KEY (guild_id, user_id)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS coin_transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    amount INTEGER NOT NULL,
                    transaction_type TEXT NOT NULL,
                    description TEXT,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.commit()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _migrate_from_json_if_needed(self) -> None:
        json_path = os.path.join(os.path.dirname(__file__), "..", "data", "coins.json")
        if not os.path.exists(json_path):
            return

        with self._connect() as conn:
            existing = conn.execute("SELECT COUNT(*) as count FROM user_balances").fetchone()
            if existing["count"] > 0:
                return

            with open(json_path, "r", encoding="utf-8") as f:
                raw = json.load(f)

            for guild_id_str, users in raw.items():
                guild_id = int(guild_id_str)
                for user_id_str, coins in users.items():
                    user_id = int(user_id_str)
                    conn.execute(
                        """
                        INSERT INTO user_balances (guild_id, user_id, coins, total_earned)
                        VALUES (?, ?, ?, ?)
                        """,
                        (guild_id, user_id, int(coins), int(coins)),
                    )
            conn.commit()

    async def get_user_coins(self, user_id: int, guild_id: int) -> int:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT coins FROM user_balances WHERE guild_id = ? AND user_id = ?",
                (guild_id, user_id),
            ).fetchone()
            return int(row["coins"]) if row else 0

    async def add_coins(self, user_id: int, guild_id: int, amount: int, transaction_type: str, description: str) -> bool:
        if amount <= 0:
            return True

        with self._connect() as conn:
            with conn:
                conn.execute(
                    """
                    INSERT INTO user_balances (guild_id, user_id, coins, total_earned)
                    VALUES (?, ?, 0, 0)
                    ON CONFLICT(guild_id, user_id) DO NOTHING
                    """,
                    (guild_id, user_id),
                )
                conn.execute(
                    "UPDATE user_balances SET coins = coins + ?, total_earned = total_earned + ? WHERE guild_id = ? AND user_id = ?",
                    (amount, amount, guild_id, user_id),
                )
                conn.execute(
                    """
                    INSERT INTO coin_transactions (guild_id, user_id, amount, transaction_type, description)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (guild_id, user_id, amount, transaction_type, description),
                )
            return True

    async def remove_coins(self, user_id: int, guild_id: int, amount: int, transaction_type: str, description: str) -> bool:
        if amount <= 0:
            return True

        with self._connect() as conn:
            with conn:
                row = conn.execute(
                    "SELECT coins FROM user_balances WHERE guild_id = ? AND user_id = ?",
                    (guild_id, user_id),
                ).fetchone()
                if not row or int(row["coins"]) < amount:
                    return False

                conn.execute(
                    "UPDATE user_balances SET coins = coins - ? WHERE guild_id = ? AND user_id = ?",
                    (amount, guild_id, user_id),
                )
                conn.execute(
                    """
                    INSERT INTO coin_transactions (guild_id, user_id, amount, transaction_type, description)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (guild_id, user_id, -amount, transaction_type, description),
                )
                return True

    def _can_claim_daily(self, user_id: int, guild_id: int) -> bool:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT last_claim_date FROM user_balances WHERE guild_id = ? AND user_id = ?",
                (guild_id, user_id),
            ).fetchone()
            if not row or not row["last_claim_date"]:
                return True

            last_claim = datetime.fromisoformat(row["last_claim_date"])
            if last_claim.tzinfo is None:
                last_claim = last_claim.replace(tzinfo=timezone.utc)
            return datetime.now(timezone.utc) - last_claim >= timedelta(hours=24)

    @app_commands.command(name="코인", description="현재 보유 코인을 확인합니다.")
    async def balance(self, interaction: discord.Interaction) -> None:
        if not interaction.guild:
            await interaction.response.send_message("이 명령은 서버에서만 사용할 수 있습니다.", ephemeral=True)
            return

        coins = await self.get_user_coins(interaction.user.id, interaction.guild.id)
        embed = discord.Embed(
            title="💰 코인 잔액",
            description=f"{interaction.user.display_name} 님의 현재 잔액은 **{coins:,} 코인**입니다.",
            color=discord.Color.gold(),
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="코인주기", description="다른 사용자에게 코인을 보내세요.")
    async def transfer(self, interaction: discord.Interaction, user: discord.Member, amount: int) -> None:
        if not interaction.guild:
            await interaction.response.send_message("이 명령은 서버에서만 사용할 수 있습니다.", ephemeral=True)
            return
        if amount <= 0:
            await interaction.response.send_message("보낼 코인은 1 이상이어야 합니다.", ephemeral=True)
            return

        sender_balance = await self.get_user_coins(interaction.user.id, interaction.guild.id)
        if sender_balance < amount:
            await interaction.response.send_message("보유 코인이 부족합니다.", ephemeral=True)
            return

        await self.remove_coins(interaction.user.id, interaction.guild.id, amount, "transfer_out", "Transfer out")
        await self.add_coins(user.id, interaction.guild.id, amount, "transfer_in", "Transfer in")

        await interaction.response.send_message(
            f"{user.mention} 님에게 {amount:,} 코인을 보냈습니다.",
            ephemeral=False,
        )

    @app_commands.command(name="일일코인", description="하루에 한 번 일일 보상을 받습니다.")
    async def daily(self, interaction: discord.Interaction) -> None:
        if not interaction.guild:
            await interaction.response.send_message("이 명령은 서버에서만 사용할 수 있습니다.", ephemeral=True)
            return

        if not self._can_claim_daily(interaction.user.id, interaction.guild.id):
            await interaction.response.send_message("오늘은 이미 일일 보상을 받았습니다.", ephemeral=True)
            return

        reward = 50
        await self.add_coins(interaction.user.id, interaction.guild.id, reward, "daily_claim", "Daily claim")
        with self._connect() as conn:
            conn.execute(
                "UPDATE user_balances SET last_claim_date = ? WHERE guild_id = ? AND user_id = ?",
                (datetime.now(timezone.utc).isoformat(), interaction.guild.id, interaction.user.id),
            )
            conn.commit()

        embed = discord.Embed(
            title="💰 일일 보상",
            description=f"{reward:,} 코인을 받았습니다. 내일 다시 받을 수 있습니다.",
            color=discord.Color.green(),
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(CoinsCog(bot))
