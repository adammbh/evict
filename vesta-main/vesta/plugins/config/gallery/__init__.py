import asyncio
import re

from asyncpg import UniqueViolationError
from xxhash import xxh32_hexdigest
from contextlib import suppress

from discord import Embed, HTTPException, Message, TextChannel
from discord.ext.commands import Cog, has_permissions, hybrid_group

from vesta.framework import Vesta, Context

IMAGE_PATTERN = re.compile(
    r"(?:([^:/?#]+):)?(?://([^/?#]*))?([^?#]*\.(?:png|jpe?g|gif))(?:\?([^#]*))?(?:#(.*))?"
)

class Gallery(Cog):
    """
    Restrict channels to only allow images.
    """

    def __init__(self, bot: Vesta) -> None:
        self.bot = bot

    @hybrid_group(aliases=["imgonly"], invoke_without_command=True)
    @has_permissions(manage_channels=True)
    async def gallery(self, ctx: Context) -> Message:
        """
        Restrict channels to only allow images.
        """
        return await ctx.send_help(ctx.command)

    @gallery.command(
        name="add",
        aliases=["create"],
    )
    @has_permissions(manage_channels=True)
    async def gallery_add(self, ctx: Context, *, channel: TextChannel) -> Message:
        """
        Add a gallery channel.
        """
        try:
            await self.bot.pool.execute(
                """
                INSERT INTO gallery (guild_id, channel_id)
                VALUES ($1, $2)
                """,
                ctx.guild.id,
                channel.id,
            )
        except UniqueViolationError:
            return await ctx.embed(
                "That channel is already a gallery channel!", message_type="warned"
            )

        return await ctx.embed(
            f"Now restricting {channel.mention} to only allow images",
            message_type="approved",
        )

    @gallery.command(
        name="remove",
        aliases=["delete", "del", "rm"],
        example="#gallery",
    )
    @has_permissions(manage_channels=True)
    async def gallery_remove(self, ctx: Context, *, channel: TextChannel) -> Message:
        """
        Remove a gallery channel.
        """
        record = await self.bot.pool.execute(
            """
            DELETE FROM gallery
            WHERE guild_id = $1
            AND channel_id = $2
            """,
            ctx.guild.id,
            channel.id,
        )
        if record == "DELETE 0":
            return await ctx.embed(
                "That channel isn't a gallery channel!", message_type="warned"
            )

        return await ctx.embed(
            f"No longer restricting {channel.mention} to only allow images",
            message_type="approved",
        )

    @gallery.command(
        name="clear",
        aliases=["clean", "reset"],
    )
    @has_permissions(manage_guild=True)
    async def gallery_clear(self, ctx: Context) -> Message:
        """
        Remove all gallery channels.
        """
        record = await self.bot.pool.execute(
            """
            DELETE FROM gallery
            WHERE guild_id = $1
            """,
            ctx.guild.id,
        )
        if record == "DELETE 0":
            return await ctx.embed(
                "No gallery channels exist for this server!", message_type="warned"
            )

        return await ctx.embed(
            "Successfully removed all gallery channels!", message_type="approved"
        )

    @gallery.command(
        name="list",
        aliases=["ls"],
    )
    @has_permissions(manage_guild=True)
    async def gallery_list(self, ctx: Context) -> Message:
        """
        View all gallery channels.
        """
        entries = [
            f"{channel.mention} (`{channel.id}`)"
            for record in await self.bot.pool.fetch(
                """
                SELECT channel_id
                FROM gallery
                WHERE guild_id = $1
                """,
                ctx.guild.id,
            )
            if (channel := ctx.guild.get_channel(record["channel_id"]))
        ]
        if not entries:
            return await ctx.embed(
                "No gallery channels exist for this server!", message_type="warned"
            )

        return await ctx.paginate(
            entries,
            embed=Embed(title=f"{len(entries)} Gallery Channels"),
        )

    @Cog.listener("on_message")
    async def gallery_listener(self, message: Message) -> None:
        """
        Delete messages that aren't images in gallery channels.
        """
        if (
            not message.guild
            or message.author.bot
            or not isinstance(
                message.channel,
                TextChannel,
            )
        ):
            return

        if not await self.bot.pool.fetchrow(
            """
            SELECT channel_id
            FROM gallery
            WHERE guild_id = $1
            AND channel_id = $2
            """,
            message.guild.id,
            message.channel.id,
        ):
            return

        if message.attachments or IMAGE_PATTERN.match(message.content):
            return

        key = xxh32_hexdigest(f"gallery:{message.channel.id}")
        if not await self.bot.redis.ratelimited(key, 6, 10):
            await message.delete()

        locked = await self.bot.redis.get(key)
        if locked:
            return

        await self.bot.redis.set(key, 1, 15)
        await asyncio.sleep(15)

        with suppress(HTTPException):
            await message.channel.purge(
                limit=200,
                check=lambda m: (
                    not m.attachments
                    and not IMAGE_PATTERN.match(m.content)
                    and not m.author.bot
                ),
                after=message,
            )
