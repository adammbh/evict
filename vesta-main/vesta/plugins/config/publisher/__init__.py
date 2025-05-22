from logging import getLogger
from contextlib import suppress

from asyncpg import UniqueViolationError
from discord import ChannelType, Embed, HTTPException, Message, TextChannel
from discord.ext.commands import Cog, group, has_permissions

from vesta.framework import Vesta, Context
from vesta.framework.tools.formatter import plural

log = getLogger("vesta/publisher")


class Publisher(Cog):
    """
    Automatically publish announcments.
    """

    def __init__(self, bot: Vesta):
        self.bot = bot

    @Cog.listener("on_message")
    async def publisher_listener(self, message: Message) -> None:
        """
        Automatically publish an announcment message.
        """
        if not message.guild or message.channel.type != ChannelType.news:
            return

        record = await self.bot.pool.fetch(
            """
            SELECT *
            FROM publisher
            WHERE channel_id = $1
            """,
            message.channel.id,
        )
        if not record:
            return

        with suppress(HTTPException):
            await message.publish()

    @group(
        aliases=["announcement"],
        invoke_without_command=True,
    )
    @has_permissions(manage_channels=True)
    async def publisher(self, ctx: Context) -> Message:
        """
        Automatically publish announcement messages.
        """
        return await ctx.send_help(ctx.command)

    @publisher.command(
        name="add",
        aliases=["create", "watch"],
    )
    @has_permissions(manage_channels=True)
    async def publisher_add(self, ctx: Context, *, channel: TextChannel) -> Message:
        """
        Add a channel to be watched.
        """
        if channel.type != ChannelType.news:
            return await ctx.embed(f"{channel.mention} isn't a news channel!", "warned")

        try:
            await self.bot.pool.execute(
                """
                INSERT INTO publisher (
                    guild_id,
                    channel_id
                )
                VALUES ($1, $2)
                """,
                ctx.guild.id,
                channel.id,
            )
        except UniqueViolationError:
            return await ctx.embed(
                f"Already publishing messages in {channel.mention}!", "warned"
            )

        return await ctx.embed(
            f"Now automatically publishing messages in {channel.mention}", "approved"
        )

    @publisher.command(
        name="remove",
        aliases=[
            "delete",
            "del",
            "rm",
            "unwatch",
        ],
    )
    @has_permissions(manage_channels=True)
    async def publisher_remove(self, ctx: Context, *, channel: TextChannel) -> Message:
        """
        Remove a channel from being watched.
        """
        record = await self.bot.pool.execute(
            """
            DELETE FROM publisher
            WHERE guild_id = $1
            AND channel_id = $2
            """,
            ctx.guild.id,
            channel.id,
        )
        if record == "DELETE 0":
            return await ctx.embed(
                f"Channel {channel.mention} isn't being watched!", "warned"
            )

        return await ctx.embed(
            f"No longer publishing messages in {channel.mention}", "approved"
        )

    @publisher.command(
        name="clear",
        aliases=["clean", "reset"],
    )
    @has_permissions(manage_channels=True)
    async def publisher_clear(self, ctx: Context) -> Message:
        """
        Stop watching all channels.
        """
        await ctx.prompt(
            "Are you sure you want to stop watching all channels?",
        )

        record = await self.bot.pool.execute(
            """
            DELETE FROM publisher
            WHERE guild_id = $1
            """,
            ctx.guild.id,
        )
        if record == "DELETE 0":
            return await ctx.embed("No channels are being watched!", "warned")

        return await ctx.embed(
            f"No longer watching {plural(record, md='`'):channel}", "approved"
        )

    @publisher.command(
        name="list",
        aliases=["ls"],
    )
    @has_permissions(manage_channels=True)
    async def publisher_list(self, ctx: Context) -> Message:
        """
        View all channels being watched.
        """
        entries = [
            f"{channel.mention} (`{channel.id}`)"
            for record in await self.bot.pool.fetch(
                """
                SELECT channel_id
                FROM publisher
                WHERE guild_id = $1
                """,
                ctx.guild.id,
            )
            if (channel := ctx.guild.get_channel(record["channel_id"]))
        ]
        if not entries:
            return await ctx.embed("No channels are being watched!", "warned")

        return await ctx.paginate(
            entries=entries,
            embed=Embed(
                title=f"{len(entries)} Watched Channel{'s' if len(entries) != 1 else ''}",
            ),
        )
