import discord

from typing import Annotated, List, Optional, cast
from asyncpg import UniqueViolationError

from discord import Embed, Member, Message, Role, TextChannel
from discord.ext.commands import Cog, Command, group, has_permissions

from .classes import CommandConverter
from vesta.framework import Vesta, Context
from vesta.framework.tools.formatter import plural
from vesta.framework.tools.conversion.discord import TouchableMember


class CommandManagement(Cog):
    """
    Allows server administrators to disable or enable specific commands.
    """

    def __init__(self, bot: Vesta):
        self.bot = bot

    async def cog_load(self) -> None:
        self.bot.add_check(self.check_command_restrictions)
        return await super().cog_load()

    async def cog_unload(self) -> None:
        self.bot.remove_check(self.check_command_restrictions)
        return await super().cog_unload()

    async def check_command_restrictions(self, ctx: Context) -> bool:
        """
        Check the restrictions for a command.

        If the command is disabled in the current channel,
        or the user doesn't have a role which is allowed to use the command.
        """
        if not ctx.guild or not ctx.command:
            return True

        if isinstance(ctx.interaction, discord.Interaction):
            if not ctx.guild.me or not isinstance(ctx.author, Member):
                return True

        if not isinstance(ctx.author, Member):
            return True

        try:
            if ctx.author.guild_permissions.administrator:
                return True

        except AttributeError:
            return True

        if await self.bot.pool.fetchrow(
            """
            SELECT 1
            FROM commands.ignore
            WHERE guild_id = $1
            AND (
                target_id = $2
                OR target_id = $3
            )
            """,
            ctx.guild.id,
            ctx.author.id,
            ctx.channel.id,
        ):
            return False

        elif await self.bot.pool.fetchrow(
            """
            SELECT 1
            FROM commands.disabled
            WHERE guild_id = $1
            AND channel_id = $2
            AND (
                command = $3
                OR command = $4
            )
            """,
            ctx.guild.id,
            ctx.channel.id,
            ctx.command.qualified_name,
            (
                ctx.command.parent.qualified_name  # type: ignore
                if ctx.command.parent
                else None
            ),
        ):
            return False

        elif await self.bot.pool.fetchrow(
            """
                SELECT 1
                FROM commands.restricted
                WHERE guild_id = $1
                AND NOT role_id = ANY($2::BIGINT[])
                AND (
                    command = $3
                    OR command = $4
                )
                """,
            ctx.guild.id,
            [role.id for role in ctx.author.roles],
            ctx.command.qualified_name,
            (
                ctx.command.parent.qualified_name  # type: ignore
                if ctx.command.parent
                else None
            ),
        ):
            return False

        return True

    @group(invoke_without_command=True)
    @has_permissions(manage_guild=True)
    async def ignore(
        self,
        ctx: Context,
        *,
        target: TextChannel | Annotated[Member, TouchableMember],
    ) -> Message:
        """
        Prevent a channel or member from invoking commands.
        """
        result = cast(
            bool,
            await self.bot.pool.fetchval(
                """
                INSERT INTO commands.ignore (guild_id, target_id)
                VALUES ($1, $2)
                ON CONFLICT (guild_id, target_id) DO NOTHING
                RETURNING TRUE
                """,
                ctx.guild.id,
                target.id,
            ),
        )
        if not result:
            return await ctx.embed(
                f"{target.mention} is already being ignored!", "warned"
            )

        return await ctx.embed(f"Now ignoring {target.mention}", "approved")

    @ignore.command(
        name="remove",
        aliases=[
            "delete",
            "del",
            "rm",
        ],
    )
    @has_permissions(manage_guild=True)
    async def ignore_remove(
        self,
        ctx: Context,
        *,
        target: TextChannel | Annotated[Member, TouchableMember],
    ) -> Message:
        """
        Remove an entity from being ignored.
        """
        result = await self.bot.pool.execute(
            """
            DELETE FROM commands.ignore
            WHERE guild_id = $1
            AND target_id = $2
            """,
            ctx.guild.id,
            target.id,
        )
        if not result:
            return await ctx.embed(f"{target.mention} isn't being ignored!", "warned")

        return await ctx.embed(
            f"Now allowing {target.mention} to invoke commands", "approved"
        )

    @ignore.command(
        name="list",
        aliases=["ls"],
    )
    @has_permissions(manage_guild=True)
    async def ignore_list(self, ctx: Context) -> Message:
        """
        View all entities being ignored.
        """
        targets = [
            f"**{target}** (`{target.id}`)"
            for record in await self.bot.pool.fetch(
                """
                SELECT target_id
                FROM commands.ignore
                WHERE guild_id = $1
                """,
                ctx.guild.id,
            )
            if (target := ctx.guild.get_member(record["target_id"]))
            or (target := ctx.guild.get_channel(record["target_id"]))
        ]
        if not targets:
            return await ctx.embed("No members are being ignored!", "warned")

        return await ctx.paginate(
            entries=targets, embed=Embed(title="Ignored Entities")
        )

    @group(
        aliases=["cmd"],
        invoke_without_command=True,
    )
    @has_permissions(manage_guild=True)
    async def command(self, ctx: Context) -> Message:
        """
        Fine tune commands which can be used in your server.

        If you were to run this command on a command like `voicemaster`,
        it would disable or restrict every subcommand as well.

        Moderators are able to use the command regardless of the settings.
        """
        return await ctx.send_help(ctx.command)

    @command.group(
        name="disable",
        invoke_without_command=True,
    )
    @has_permissions(manage_guild=True)
    async def command_disable(
        self,
        ctx: Context,
        channel: Optional[TextChannel],
        *,
        command: Annotated[
            Command,
            CommandConverter,
        ],
    ) -> Message:
        """
        Disable a command in a specific channel.

        If no channel is provided, the command will be disabled globally.
        """
        if channel is None and not ctx.guild.text_channels:
            return await ctx.embed("This server has no text channels!", "warned")

        channel_ids: List[int] = [
            record["channel_id"]
            for record in await self.bot.pool.fetch(
                """
                SELECT channel_id
                FROM commands.disabled
                WHERE guild_id = $1
                AND command = $2
                """,
                ctx.guild.id,
                command.qualified_name,
            )
        ]
        if channel and channel.id in channel_ids:
            return await ctx.embed(
                f"The command **{command.qualified_name}** is already disabled in {channel.mention}!",
                "warned",
            )

        elif not channel and all(
            channel_id in channel_ids for channel_id in ctx.guild.text_channels
        ):
            return await ctx.embed(
                f"The command **{command.qualified_name}** is already disabled in all channels!",
                "warned",
            )

        await self.bot.pool.executemany(
            """
            INSERT INTO commands.disabled (guild_id, channel_id, command)
            VALUES ($1, $2, $3)
            ON CONFLICT (guild_id, channel_id, command)
            DO NOTHING
            """,
            [
                (ctx.guild.id, channel.id, command.qualified_name)
                for channel in (
                    ctx.guild.text_channels if channel is None else [channel]
                )
            ],
        )

        if not channel:
            return await ctx.embed(
                f"Disabled command **{command.qualified_name}** in {plural(len(ctx.guild.text_channels), md='**'):channel}",
                "approved",
            )

        return await ctx.embed(
            f"Disabled command **{command.qualified_name}** in {channel.mention}",
            "approved",
        )

    @command_disable.command(
        name="list",
        aliases=["ls"],
    )
    @has_permissions(manage_guild=True)
    async def command_disable_list(self, ctx: Context) -> Message:
        """
        View all command restrictions.
        """
        commands = [
            f"**{record['command']}** - {', '.join(channel.mention for channel in channels[:2])}"
            + (f" (+{len(channels) - 2})" if len(channels) > 2 else "")
            for record in await self.bot.pool.fetch(
                """
                SELECT command, ARRAY_AGG(channel_id) AS channel_ids
                FROM commands.disabled
                WHERE guild_id = $1
                GROUP BY guild_id, command
                """,
                ctx.guild.id,
            )
            if (
                channels := [
                    channel
                    for channel_id in record["channel_ids"]
                    if (channel := ctx.guild.get_channel(channel_id))
                ]
            )
        ]
        if not commands:
            return await ctx.embed(
                "No commands are disabled for this server!", "warned"
            )

        return await ctx.paginate(
            entries=commands, embed=Embed(title="Disabled Commands")
        )

    @command.command(name="enable", example="#general ban")
    @has_permissions(manage_guild=True)
    async def command_enable(
        self,
        ctx: Context,
        channel: Optional[TextChannel],
        *,
        command: Annotated[
            Command,
            CommandConverter,
        ],
    ) -> Message:
        """
        Enable a command in a specific channel.

        If no channel is provided, the command will be enabled globally.
        """
        channel_ids: List[int] = [
            record["channel_id"]
            for record in await self.bot.pool.fetch(
                """
                SELECT channel_id
                FROM commands.disabled
                WHERE guild_id = $1
                AND command = $2
                """,
                ctx.guild.id,
                command.qualified_name,
            )
        ]
        if channel and channel.id not in channel_ids:
            return await ctx.embed(
                f"The command **{command.qualified_name}** is already enabled in {channel.mention}!",
                "warned",
            )

        elif not channel and not channel_ids:
            return await ctx.embed(
                f"The command **{command.qualified_name}** is already enabled in all channels!",
                "warned",
            )

        await self.bot.pool.execute(
            """
            DELETE FROM commands.disabled
            WHERE guild_id = $1
            AND command = $2
            AND channel_id = ANY($3::BIGINT[])
            """,
            ctx.guild.id,
            command.qualified_name,
            channel_ids if channel is None else [channel.id],
        )

        if not channel:
            return await ctx.embed(
                f"Enabled command **{command.qualified_name}** in {plural(len(channel_ids), md='**'):channel}",
                "approved",
            )

        return await ctx.embed(
            f"Enabled command **{command.qualified_name}** in {channel.mention}",
            "approved",
        )

    @command.group(
        name="restrict",
        aliases=["allow"],
        invoke_without_command=True,
        example="@admin ban",
    )
    @has_permissions(manage_guild=True)
    async def command_restrict(
        self,
        ctx: Context,
        role: Role,
        *,
        command: Annotated[
            Command,
            CommandConverter,
        ],
    ) -> Message:
        """
        Restrict a command to a specific role.
        This will remove an existing restriction if one exists.
        """
        try:
            await self.bot.pool.execute(
                """
                INSERT INTO commands.restricted (guild_id, role_id, command)
                VALUES ($1, $2, $3)
                """,
                ctx.guild.id,
                role.id,
                command.qualified_name,
            )
        except UniqueViolationError:
            await self.bot.pool.execute(
                """
                DELETE FROM commands.restricted
                WHERE guild_id = $1
                AND role_id = $2
                AND command = $3
                """,
                ctx.guild.id,
                role.id,
                command.qualified_name,
            )
            return await ctx.embed(
                f"Removed the restriction on **{command.qualified_name}** for {role.mention}",
                "approved",
            )

        return await ctx.embed(
            f"Now allowing {role.mention} to use **{command.qualified_name}**",
            "approved",
        )

    @command_restrict.command(
        name="list",
        aliases=["ls"],
    )
    @has_permissions(manage_guild=True)
    async def command_restrict_list(self, ctx: Context) -> Message:
        """
        View all command restrictions.
        """
        entries = [
            f"**{record['command']}** - {', '.join(role.mention for role in roles)}"
            for record in await self.bot.pool.fetch(
                """
                SELECT command, ARRAY_AGG(role_id) AS role_ids
                FROM commands.restricted
                WHERE guild_id = $1
                GROUP BY guild_id, command
                """,
                ctx.guild.id,
            )
            if (
                roles := [
                    role
                    for role_id in record["role_ids"]
                    if (role := ctx.guild.get_role(role_id))
                ]
            )
        ]
        if not entries:
            return await ctx.embed("No restrictions exist for this server!", "warned")

        return await ctx.paginate(
            entries=entries, embed=Embed(title=f"{len(entries)} Command Restrictions")
        )
