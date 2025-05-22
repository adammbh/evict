from contextlib import suppress
from json import dumps
from logging import getLogger
from secrets import token_urlsafe
from typing import Optional, cast

from discord import Embed, HTTPException, Message
from discord.ext.commands import BucketType, cooldown, group, Cog
from discord.utils import format_dt

from .models import BackupLoader, BackupViewer, dump
from .types import BooleanArgs
from ..security.antinuke import Settings
from vesta.framework import Vesta, Context

log = getLogger("vesta/backup")


class Backup(Cog):
    """
    Restore previous backups of the server.
    """

    def __init__(self, bot: Vesta) -> None:
        self.bot = bot

    async def cog_load(self) -> None:
        self.bot.add_check(self.check_backup_restrictions)
        return await super().cog_load()

    async def cog_unload(self) -> None:
        self.bot.remove_check(self.check_backup_restrictions)
        return await super().cog_unload()

    async def check_backup_restrictions(self, ctx: Context) -> bool:
        """
        Check the restrictions for the backup command.
        """
        if not ctx.command.qualified_name.startswith("backup"):
            return True

        config = await Settings.fetch(self.bot, ctx.guild)
        if not config.is_trusted(ctx.author):
            await ctx.embed(
                "You must be a **trusted administrator** to use this command!",
                message_type="warned",
            )
            return False

        return True

    @group(invoke_without_command=True)
    async def backup(self, ctx: Context) -> Message:
        """
        Backup the server layout and settings.
        """
        return await ctx.send_help(ctx.command)

    @backup.command(name="create", aliases=["make", "take", "new"])
    async def backup_create(self, ctx: Context) -> Message:
        """
        Create a new restore point.
        """
        backup_count = cast(
            int,
            await self.bot.pool.fetchval(
                """
                SELECT COUNT(*)
                FROM backup
                WHERE user_id = $1
                """,
                ctx.author.id,
            ),
        )
        if backup_count >= 10:
            return await ctx.embed(
                "You have reached the maximum amount of backups!",
                f"Use `{ctx.clean_prefix}backup remove` to remove a backup",
                message_type="warned",
            )

        async with ctx.typing():
            key = token_urlsafe(12)
            backup = await dump(ctx.guild)

            await self.bot.pool.execute(
                """
                INSERT INTO backup (key, guild_id, user_id, data)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (key, guild_id) DO UPDATE
                SET data = EXCLUDED.data
                """,
                key,
                ctx.guild.id,
                ctx.author.id,
                (dumps(backup).encode()).decode(),
            )

        if ctx.author.is_on_mobile():
            with suppress(HTTPException):
                await ctx.author.send(f"{ctx.prefix}backup restore {key}")

        return await ctx.embed(
            f"Successfully created a restore point with key `{key}`",
            f"Use `{ctx.prefix}backup restore {key}` to restore this backup",
            message_type="approved",
        )

    @backup.command(name="view", aliases=["info", "display"], example="123456789012")
    async def backup_view(self, ctx: Context, key: str) -> Message:
        """
        View an existing restore point.
        """
        record = await self.bot.pool.fetchrow(
            """
            SELECT *
            FROM backup
            WHERE key = $1
            AND user_id = $2
            """,
            key,
            ctx.author.id,
        )
        if not record:
            return await ctx.embed(
                "You don't have a backup with that identifier!", message_type="warned"
            )

        backup = BackupViewer(record["data"])
        embed = Embed(
            title=backup.name,
            description=f"{format_dt(record['created_at'])} ({format_dt(record['created_at'], 'R')})",
        )
        embed.add_field(name="**Channels**", value=backup.channels())
        embed.add_field(name="**Roles**", value=backup.roles())

        return await ctx.send(embed=embed)

    @backup.command(
        name="restore", aliases=["load", "apply", "set"], example="123456789012"
    )
    @cooldown(1, 5 * 60, BucketType.guild)
    async def backup_restore(
        self,
        ctx: Context,
        key: str,
        *options,
    ) -> Optional[Message]:
        """
        Load an existing restore point.
        """
        record = await self.bot.pool.fetchrow(
            """
            SELECT *
            FROM backup
            WHERE key = $1
            AND user_id = $2
            """,
            key,
            ctx.author.id,
        )
        if not record:
            return await ctx.embed(
                "You don't have a backup with that identifier!", message_type="warned"
            )

        options = BooleanArgs(["channels", "roles", "settings"] + list(options))
        warnings: list[str] = []
        if options.channels:
            warnings.append("Channels will be deleted")
        if options.roles:
            warnings.append("Roles will be deleted")
        if options.bans:
            warnings.append("Bans will be restored")
        if options.settings:
            warnings.append("Server settings will be updated")

        if not warnings:
            return await ctx.embed(
                "You must specify at least one option to restore!",
                message_type="warned",
            )

        await ctx.prompt(
            f"Are you sure you want to load backup `{key}`?"
            f"\n**The following changes will occur**",
            "\n".join(warnings),
        )

        backup = BackupLoader(self.bot, ctx.guild, record["data"])

        await ctx.embed(f"Preparing to load backup `{key}`..", message_type="approved")
        await backup.load(ctx.author, options)

        if ctx.guild.text_channels:
            return await ctx.guild.text_channels[0].send(
                content=ctx.author.mention,
                embed=Embed(
                    title="Backup Loaded",
                    description="Successfully  loaded the backup",
                ),
                delete_after=10,
            )

    @backup.command(
        name="remove",
        aliases=["delete", "del", "rm"],
        example="123456789012",
    )
    async def backup_remove(self, ctx: Context, key: str) -> Message:
        """
        Remove a restore point.
        """
        result = await self.bot.pool.execute(
            """
            DELETE FROM backup
            WHERE key = $1
            AND user_id = $2
            """,
            key,
            ctx.author.id,
        )
        if result == "DELETE 0":
            return await ctx.embed(
                "You don't have a backup with that identifier!", message_type="warned"
            )

        return await ctx.embed(
            f"Successfully removed the restore point with key `{key}`",
            message_type="approved",
        )

    @backup.command(
        name="list",
        aliases=["ls"],
    )
    async def backup_list(self, ctx: Context) -> Message:
        """
        View your restore points.
        """
        channels = [
            f"**{backup.name}** (`{record['key']}`) - {format_dt(record['created_at'], 'd')}"
            for record in await self.bot.pool.fetch(
                """
                SELECT key, data, created_at
                FROM backup
                WHERE user_id = $1
                """,
                ctx.author.id,
            )
            if (backup := BackupViewer(record["data"]))
        ]
        if not channels:
            return await ctx.embed(
                "You haven't created any restore points!", message_type="warned"
            )

        return await ctx.paginate(
            entries=channels, title="Your Restore Points", max_entries=6
        )
