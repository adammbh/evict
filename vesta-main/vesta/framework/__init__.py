import logging
import glob
import os
import importlib

from typing import List, Optional, cast
from pathlib import Path
from aiohttp import ClientSession
from colorama import Fore

from discord import (
    Intents,
    Message,
    Guild,
    AuditLogEntry,
    HTTPException,
    Activity,
    ActivityType,
    AllowedMentions,
    PartialMessageable,
    ChannelType,
)
from discord.ext.commands import (
    AutoShardedBot,
    ExtensionError,
    when_mentioned_or,
)

from vesta.framework.discord import Context, CommandErrorHandler
from vesta.framework.pagination import Paginator

from vesta.shared.config import Authentication, Configuration
from vesta.shared.clients import postgres
from vesta.shared.clients.postgres import Database
from vesta.shared.clients.settings import Settings
from vesta.shared.clients.redis import Redis

logger = logging.getLogger("vesta/main")


class Vesta(AutoShardedBot):
    """
    Custom bot class that extends AutoShardedBot.
    """

    database: Database
    redis: Redis
    version: str = "0.1.0"
    session: ClientSession

    def __init__(self):
        super().__init__(
            command_prefix=";",
            owner_ids=Authentication.owner_ids,
            intents=Intents.all(),
            help_command=None,
            allowed_mentions=AllowedMentions(
                everyone=False,
                roles=False,
                users=True,
                replied_user=False,
            ),
            activity=Activity(
                type=ActivityType.streaming,
                name="🔗 evict.bot",
                url=f"https://twitch.tv/evict",
            ),
        )
        self.version = self.version

    def get_message(self, message_id: int) -> Optional[Message]:
        """
        Fetch a message from the cache.
        """
        return self._connection._get_message(message_id)

    async def prefix(self, message: Message) -> List[str]:
        prefixes = []
        if message.guild:
            prefixes.append(
                (await Configuration.from_guild(message.guild.id, self)).defaults.prefix
            )

        prefixes.append(
            (await Configuration.from_user(message.author.id, self)).defaults.prefix
        )

        return when_mentioned_or(*prefixes)(message)

    async def on_shard_ready(self, shard_id: int) -> None:
        """
        Custom on_shard_ready method that logs shard status.
        """
        logger.info(f"Shard {shard_id} is ready, starting post-connection setup...")

        try:
            logger.info(
                f"Shard ID {Fore.LIGHTGREEN_EX}{shard_id}{Fore.RESET} has {Fore.LIGHTGREEN_EX}spawned{Fore.RESET}."
            )

            if shard_id == self.shard_count - 1:
                logger.info("All shards connected, waiting for full ready state...")

        except Exception as e:
            logger.error(
                f"Error in on_shard_ready for shard {shard_id}: {e}", exc_info=True
            )

    async def on_shard_resumed(self, shard_id: int) -> None:
        """
        Custom on_shard_resumed method that logs shard status.
        """
        logger.info(
            f"Shard ID {Fore.LIGHTGREEN_EX}{shard_id}{Fore.RESET} has {Fore.LIGHTYELLOW_EX}resumed{Fore.RESET}."
        )

    async def notify(self, guild: Guild, *args, **kwargs) -> Optional[Message]:
        """
        Send a message to the first available channel.
        """
        if not isinstance(guild, Guild):
            logger.error(f"Expected Guild object, got {type(guild).__name__}")
            return

        if (
            guild.system_channel
            and guild.system_channel.permissions_for(guild.me).send_messages
        ):
            try:
                return await guild.system_channel.send(*args, **kwargs)
            except HTTPException:
                return

        for channel in guild.text_channels:
            if channel.permissions_for(guild.me).send_messages:
                try:
                    return await channel.send(*args, **kwargs)
                except HTTPException:
                    break

    async def load_patches(self) -> None:
        """
        Load all patches in the framework directory.
        """
        for module in glob.glob(
            "vesta/framework/discord/patches/**/*.py", recursive=True
        ):
            if module.endswith("__init__.py"):
                continue
            module_name = (
                module.replace(os.path.sep, ".").replace("/", ".").replace(".py", "")
            )
            try:
                importlib.import_module(module_name)
                logger.info(f"Patched: {module}")
            except (ModuleNotFoundError, ImportError) as e:
                logger.error(f"Error importing {module_name}: {e}")

    async def _load_extensions(self) -> None:
        """
        Load all plugins in the framework directory.
        """
        loaded_count = 0
        jishaku_loaded = False

        for extension in sorted(Path("vesta/plugins").glob("*")):
            if extension.name.startswith(("_", ".")):
                continue

            package = (
                extension.stem
                if extension.is_file() and extension.suffix == ".py"
                else (
                    extension.name
                    if extension.is_dir() and (extension / "__init__.py").exists()
                    else None
                )
            )

            if not package:
                continue

            try:
                if not jishaku_loaded:
                    await self.load_extension("jishaku")
                    jishaku_loaded = True
                await self.load_extension(f"vesta.plugins.{package}")
                loaded_count += 1
                logger.info(f"Loaded extension: {package}")
            except ExtensionError as exc:
                logger.error(
                    f"Failed to load extension {package}: {exc}", exc_info=True
                )

        logger.info(f"Successfully loaded {loaded_count} extensions.")

    async def setup_hook(self) -> None:
        self.session = ClientSession(
            headers={
                "User-Agent": "Mozilla/5.0 (iPhone; U; CPU iPhone OS 4_0 like Mac OS X; en-us)"
                " AppleWebKit/532.9 (KHTML, like Gecko) Version/4.0.5 Mobile/8A293 Safari/6531.22.7"
            },
        )

        self.database = await postgres.connect()
        logger.info("Connected to PostgreSQL")

        self.redis = await Redis.from_url()
        logger.info("Connected to Redis")

        await self.load_patches()
        logger.info("Loaded patches")

        await self._load_extensions()
        logger.info("Loaded packages")

        return await super().setup_hook()

    async def get_context(self, message: Message, *, cls=Context) -> Context:
        """
        Custom get_context method that adds the config attribute to the context.
        """
        context = await super().get_context(message, cls=cls)
        context.config = await Configuration.from_guild(context.guild.id, self)
        context.settings = await Settings.fetch(self, context.guild)
        return context

    async def on_command_error(self, context: Context, exception: Exception) -> None:
        """
        Custom error handler for commands.
        """
        await CommandErrorHandler.on_command_error(self, context, exception)

    async def close(self) -> None:
        """
        Cleanup resources and close the bot
        """
        await self.session.close()
        await self.database.close()
        await self.redis.close()
        await super().close()

    async def start(self, *, reconnect: bool = True) -> None:  # type: ignore
        return await super().start(Authentication.token, reconnect=reconnect)

    @property
    def pool(self) -> Database:
        """
        Convenience property to access the database.
        """
        return self.database

    async def on_audit_log_entry_create(self, entry: AuditLogEntry):
        """
        Custom on_audit_log_entry_create method that dispatches events.
        """
        if not self.is_ready():
            return

        event = f"audit_log_entry_{entry.action.name}"
        self.dispatch(event, entry)

    async def process_commands(self, message: Message) -> None:
        """
        Custom process_commands method that handles command processing.
        """
        if message.author.bot:
            return

        blacklisted = cast(
            bool,
            await self.pool.fetchval(
                """
                SELECT EXISTS(
                    SELECT 1
                    FROM blacklist
                    WHERE user_id = $1
                )
                """,
                message.author.id,
            ),
        )
        if blacklisted:
            return

        if message.guild:
            channel = message.channel
            if not (
                channel.permissions_for(message.guild.me).send_messages
                and channel.permissions_for(message.guild.me).embed_links
                and channel.permissions_for(message.guild.me).attach_files
            ):
                return

        ctx = await self.get_context(message)

        if not ctx.valid and message.content.startswith(ctx.clean_prefix):
            try:
                command = message.content[len(ctx.clean_prefix):].strip().split()[0].lower()
                # utility_cog = self.get_cog("Utility")
                # if utility_cog:
                #     result = await utility_cog.process_custom_command(ctx, command)
                #     if result:
                #         return
            except IndexError: 
                return
                
        if (
            ctx.invoked_with
            and isinstance(message.channel, PartialMessageable)
            and message.channel.type != ChannelType.private
        ):
            logger.warning(
                "Discarded a command message (ID: %s) with PartialMessageable channel: %r.",
                message.id,
                message.channel,
            )
        else:
            await self.invoke(ctx)

        if not ctx.valid:
            self.dispatch("message_without_command", ctx)


__all__ = ("Vesta", "Context", "Paginator")
