import discord
import asyncio
import uwuipy

from discord import (
    Guild,
    User,
    Member,
    Message,
    Webhook,
    TextChannel,
    Forbidden,
    AuditLogEntry,
    HTTPException,
)
from discord.ext.commands import Cog
from discord.utils import utcnow

from datetime import datetime
from xxhash import xxh64_hexdigest
from uwuipy import uwuipy
from typing import Optional
from contextlib import suppress

from vesta.framework import Vesta


class Listeners(Cog):
    def __init__(self, bot: Vesta):
        self.bot = bot

    async def webhook(self, channel: TextChannel) -> Optional[Webhook]:
        """
        Create a webhook in a channel.
        """
        if not channel.permissions_for(channel.guild.me).manage_webhooks:
            return None

        with suppress(Forbidden):
            for webhook in await channel.webhooks():
                if webhook.user == self.bot.user:
                    return webhook

            return await channel.create_webhook(name="evict")

    @Cog.listener("on_audit_log_entry_ban")
    async def owner_unban(self, entry: AuditLogEntry):
        """
        Automatically unban a bot owner when they are banned.
        """
        if (
            not isinstance(entry.target, (Member, User))
            or entry.target.id not in self.bot.owner_ids
        ):
            return

        await entry.guild.unban(
            entry.target, reason=f"Unbanned by {self.bot.user.name} (bot owner)"
        )

        if entry.guild.vanity_url:
            await entry.target.send(f"{entry.guild.vanity_url} - guild tried to ban")

        if not entry.guild.vanity_url:
            invite = await entry.guild.text_channels[0].create_invite(max_age=0)
            await entry.target.send(f"{invite} - guild tried to ban")

    @Cog.listener("on_guild_update")
    async def guild_name_listener(self, before: Guild, after: Guild):
        """
        Listen for guild name changes and log them.
        """
        if before.name != after.name:
            await self.bot.pool.execute(
                """
                INSERT INTO gnames (guild_id, name, changed_at) 
                VALUES ($1, $2, $3)
                """,
                before.id,
                before.name,
                datetime.now(),
            )

    @Cog.listener("on_user_update")
    async def name_history_listener(self, before: User, after: User) -> None:
        """
        Listen for name changes and log them.
        """
        if before.name == after.name and before.global_name == after.global_name:
            return

        await self.bot.pool.execute(
            """
            INSERT INTO name_history (user_id, username)
            VALUES ($1, $2)
            """,
            after.id,
            (
                before.name
                if after.name != before.name
                else (before.global_name or before.name)
            ),
        )

    @Cog.listener("on_guild_join")
    async def blacklist_checK(self, guild: Guild) -> None:
        """
        Check if the guild is blacklisted.
        """
        record = await self.bot.pool.fetchval(
            """
            SELECT EXISTS(SELECT 1 FROM guildblacklist WHERE guild_id = $1)
            """,
            guild.id,
        )
        if record:
            await guild.leave()

    @Cog.listener("on_message")
    async def uwulock_listener(self, message: Message):
        """
        Automatically uwuify messages from users.
        """
        if not message.guild:
            return

        record = await self.bot.pool.fetchrow(
            """
            SELECT * FROM uwulock 
            WHERE user_id = $1 
            AND guild_id = $2
            """,
            message.author.id,
            message.guild.id,
        )
        if not record:
            return

        uwu = uwuipy()
        uwu_message = uwu.uwuify(message.content)
        hook = await self.webhook(message.channel)

        key = xxh64_hexdigest(f"uwulock:{message.author.id}{message.channel.id}")

        if await self.bot.redis.ratelimited(key, 3, 2):
            await asyncio.sleep(2)

        if hook and uwu_message.strip():
            with suppress(Forbidden):
                await hook.send(
                    content=uwu_message,
                    username=message.author.display_name,
                    avatar_url=message.author.display_avatar,
                    thread=(
                        message.channel
                        if isinstance(message.channel, discord.Thread)
                        else discord.utils.MISSING
                    ),
                )
                await message.delete()

    @Cog.listener("on_member_unboost")
    async def boosters_lost(self, member: Member) -> None:
        """
        Log when a member stops boosting the server.
        """
        if not member.premium_since:
            return

        await self.bot.pool.execute(
            """
            INSERT INTO boosters_lost (guild_id, user_id, lasted_for)
            VALUES ($1, $2, $3)
            ON CONFLICT (guild_id, user_id) DO UPDATE
            SET lasted_for = EXCLUDED.lasted_for
            """,
            member.guild.id,
            member.id,
            utcnow() - member.premium_since,
        )

    @Cog.listener("on_member_unban")
    async def hardban_unban(self, guild: Guild, user: Member):
        """
        Automatically reban a member if they are hardbanned.
        """
        record = await self.bot.pool.fetchrow(
            """
            SELECT * 
            FROM hardban 
            WHERE guild_id = $1 
            AND user_id = $2
            """,
            guild.id,
            user.id,
        )
        if not record:
            return

        with suppress(HTTPException, Forbidden):
            await guild.ban(user, reason=f"User is hardbanned.")

    @Cog.listener("on_member_join")
    async def hardban_join(self, member: Member):
        """
        Check if a member is hard banned and ban them if they are.
        """
        record = await self.bot.pool.fetchrow(
            """
            SELECT * 
            FROM hardban 
            WHERE guild_id = $1 
            AND user_id = $2
            """,
            member.guild.id,
            member.id,
        )
        if not record:
            return

        with suppress(HTTPException, Forbidden):
            await member.ban(reason="User is hardbanned")


async def setup(bot: "Vesta") -> None:
    await bot.add_cog(Listeners(bot))
