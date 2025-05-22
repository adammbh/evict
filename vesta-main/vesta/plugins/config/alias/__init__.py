from re import search
from asyncpg import UniqueViolationError

from discord import Embed, Message
from discord.ext.commands import (
    Cog,
    has_permissions,
    hybrid_group,
)

from .entry import AliasEntry
from vesta.framework import Vesta, Context
from vesta.framework.tools.formatter import plural


class Alias(Cog):
    """
    Alias provides tools for managing command shortcuts.
    """

    def __init__(self, bot: Vesta) -> None:
        self.bot = bot

    def is_command(self, name: str) -> bool:
        """
        Check if a command exists.
        """
        command = self.bot.get_command(name)
        return command is not None

    def is_valid(self, name: str) -> bool:
        """
        Check if an alias is valid.
        """
        return not bool(search(r"\s", name)) and name.isprintable()

    @Cog.listener("on_message_without_command")
    async def alias_listener(self, ctx: Context) -> None:
        """
        Invokes an alias if one is provided.
        """
        prefix = ctx.prefix or ctx.clean_prefix
        try:
            potential_alias = ctx.message.content[len(prefix) :].split(" ")[0]
        except IndexError:
            return

        alias = await AliasEntry.get(ctx.guild, potential_alias)
        if alias:
            await alias(ctx)

    @hybrid_group(
        aliases=["shortcut"],
        invoke_without_command=True,
    )
    @has_permissions(manage_guild=True)
    async def alias(self, ctx: Context) -> Message:
        """
        The base command for managing command shortcuts.

        This is useful for commands that are used frequently or have long names.
        When ran, aliases will accept any additional arguments and append them to the stored alias.
        """
        return await ctx.send_help(ctx.command)

    @alias.command(
        name="add",
        aliases=["create"],
    )
    @has_permissions(manage_guild=True)
    async def alias_add(self, ctx: Context, name: str, *, invoke: str) -> Message:
        """
        Add an alias for a command.
        """
        if self.is_command(name):
            return await ctx.embed(
                f"A command with the name **{name}** already exists!",
                message_type="warned",
            )

        elif not self.is_valid(name):
            return await ctx.embed(
                "Invalid alias name provided!", message_type="warned"
            )

        command = self.bot.get_command(invoke.split(maxsplit=1)[0])
        if not command:
            return await ctx.embed(
                "The command provided doesn't exist!", message_type="warned"
            )

        try:
            await self.bot.pool.execute(
                """
                INSERT INTO aliases (
                    guild_id,
                    name,
                    invoke,
                    command
                )
                VALUES ($1, $2, $3, $4)
                """,
                ctx.guild.id,
                name.lower(),
                invoke,
                command.qualified_name,
            )
        except UniqueViolationError:
            return await ctx.warn(f"An alias with the name **{name}** already exists!")

        return await ctx.approve(f"Added shortcut **{name}** for `{invoke}`")

    @alias.command(name="view", aliases=["show"], example="b")
    @has_permissions(manage_guild=True)
    async def alias_view(self, ctx: Context, alias: str) -> Message:
        """
        View what an alias invokes.
        """
        record = await self.bot.pool.fetchval(
            """
            SELECT invoke
            FROM aliases
            WHERE guild_id = $1
            AND name = $2
            """,
            ctx.guild.id,
            alias.lower(),
        )
        if not record:
            return await ctx.embed(
                f"An alias matching **{alias}** doesn't exist!", message_type="warned"
            )

        return await ctx.embed(
            f"The **{alias}** shortcut invokes `{record}`", message_type="neutral"
        )

    @alias.command(
        name="remove",
        aliases=["delete", "del", "rm"],
    )
    @has_permissions(manage_guild=True)
    async def alias_remove(self, ctx: Context, alias: str) -> Message:
        """
        Remove an existing alias.
        """
        record = await self.bot.pool.execute(
            """
            DELETE FROM aliases
            WHERE guild_id = $1
            AND name = $2
            """,
            ctx.guild.id,
            alias.lower(),
        )
        if record == "DELETE 0":
            return await ctx.embed(
                f"An alias matching **{alias}** doesn't exist!", message_type="warned"
            )

        return await ctx.embed(
            f"Removed the shortcut **{alias}**", message_type="approved"
        )

    @alias.command(
        name="clear",
        aliases=["clean", "reset"],
    )
    @has_permissions(manage_guild=True)
    async def alias_clear(self, ctx: Context) -> Message:
        """
        Remove all command shortcuts.
        """
        await ctx.prompt("Are you sure you want to remove all aliases?")

        record = await self.bot.pool.execute(
            """
            DELETE FROM aliases
            WHERE guild_id = $1
            """,
            ctx.guild.id,
        )
        if record == "DELETE 0":
            return await ctx.embed(
                "No aliases exist for this server!", message_type="warned"
            )

        return await ctx.embed(
            f"Removed {plural(record, md='`'):command shortcut}",
            message_type="approved",
        )

    @alias.command(
        name="list",
        aliases=["ls"],
    )
    @has_permissions(manage_guild=True)
    async def alias_list(self, ctx: Context) -> Message:
        """
        View all command shortcuts.
        """
        record = [
            f"**{record['name']}** invokes `{record['invoke']}`"
            for record in await self.bot.pool.fetch(
                """
                SELECT name, invoke, command
                FROM aliases
                WHERE guild_id = $1
                """,
                ctx.guild.id,
            )
            if self.bot.get_command(record["command"]) is not None
        ]
        if not record:
            return await ctx.embed(
                "No aliases exist for this server!", message_type="warned"
            )

        return await ctx.paginate(
            entries=record, embed=Embed(title=f"{len(record)} Command Shortcuts")
        )
