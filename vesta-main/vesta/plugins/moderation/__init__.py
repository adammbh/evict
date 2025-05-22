import re
import json
import discord
import asyncio
import humanize

from discord import (
    AuditLogAction,
    AuditLogEntry,
    Color,
    Embed,
    Emoji,
    File,
    Guild,
    GuildSticker,
    HTTPException,
    Member,
    Message,
    NotFound,
    NotificationLevel,
    Object,
    PartialEmoji,
    RateLimited,
    Role,
    StageChannel,
    TextChannel,
    Thread,
    User,
    VoiceChannel,
)
from discord.ext.commands import (
    BadArgument,
    BucketType,
    Cog,
    CommandError,
    Greedy,
    MaxConcurrency,
    Range,
    check,
    command,
    cooldown,
    flag,
    group,
    has_permissions,
    hybrid_command,
    hybrid_group,
    max_concurrency,
    parameter,
)
from discord.abc import GuildChannel
from discord.utils import MISSING, format_dt, get, utcnow
from discord.ui import View, Button, button

from contextlib import suppress
from datetime import timedelta
from humanfriendly import format_timespan
from humanize import precisedelta
from io import BytesIO
from time import perf_counter
from typing import (
    Annotated, 
    Callable, 
    List, 
    Literal, 
    Optional, 
    cast
)
from xxhash import xxh64_hexdigest
from zipfile import ZipFile

from .classes import ModerationClass
from vesta.framework import Vesta, Context
from vesta.framework.script import Script
from vesta.framework.tools import (
    convert_image,
    enlarge_emoji,
    quietly_delete,
    strip_roles,
    unicode_emoji,
    url_to_mime,
)
from vesta.framework.tools.formatter import (
    codeblock, 
    human_join, 
    plural
)
from vesta.framework.tools.conversion import (
    Duration, 
    StrictMember, 
    StrictRole, 
    StrictUser
)
from vesta.framework.tools.conversion.discord import TouchableMember, GoodRole
from vesta.framework.tools import strip_roles
from vesta.framework.tools.conversion import PartialAttachment, StrictRole
from vesta.framework.tools.converters import Color as ColorConverter, DANGEROUS_PERMISSIONS
from vesta.framework.discord.flags import FlagConverter
from vesta.plugins.config.security.antinuke import Settings

class Moderation(Cog):
    def __init__(self, bot: Vesta):
        self.bot = bot

# log = getLogger("evict/mod")
MASS_ROLE_CONCURRENCY = MaxConcurrency(1, per=BucketType.guild, wait=False)

FAKE_PERMISSIONS_TABLE = "fake_permissions"
fake_permissions = [
    "administrator",
    "ban_members",
    "kick_members",
    "manage_guild",
    "manage_channels",
    "manage_roles",
    "manage_messages",
    "view_audit_log",
    "manage_webhooks",
    "manage_expressions",
    "mute_members",
    "deafen_members",
    "move_members",
    "manage_nicknames",
    "mention_everyone",
    "view_guild_insights",
    "external_emojis",
    "moderate_members",
]

class WarnActionFlags(FlagConverter):
    threshold: Range[int, 1, 50] = flag(
        description="The number of warns needed to trigger this action"
    )
    duration: Optional[Duration] = flag(
        default=None,
        description="Duration for timeout/jail/ban actions"
    )

class ModStatsView(View):
    def __init__(self, bot: Vesta, moderator_id):
        super().__init__()
        self.bot = bot
        self.moderator_id = moderator_id
        self._message_cache = {}

    @button(
        label="Details", style=discord.ButtonStyle.primary, custom_id="modstats_details"
    )
    async def modstats_details(self, button, interaction):
        detailed_stats = await self.bot.pool.fetch(
            """
            SELECT action, COUNT(*) AS count
            FROM history.moderation
            WHERE moderator_id = $1
            GROUP BY action
            """,
            self.moderator_id,
        )

        details_embed = Embed(title="Detailed Moderation Stats")
        for stat in detailed_stats:
            details_embed.add_field(
                name=stat["action"], value=str(stat["count"]), inline=True
            )

        await interaction.response.send_message(embed=details_embed)


class Moderation(Cog):
    def __init__(self, bot: Vesta):
        self.bot = bot
        self.description = "Moderation commands to make things easier."

    @property
    def actions(self) -> dict[str, str]:
        return {
            "guild_update": "updated server",
            "channel_create": "created channel",
            "channel_update": "updated channel",
            "channel_delete": "deleted channel",
            "overwrite_create": "created channel permission in",
            "overwrite_update": "updated channel permission in",
            "overwrite_delete": "deleted channel permission in",
            "kick": "kicked member",
            "member_prune": "pruned members in",
            "ban": "banned member",
            "unban": "unbanned member",
            "member_update": "updated member",
            "member_role_update": "updated member roles for",
            "member_disconnect": "disconnected member",
            "member_move": "moved member",
            "bot_add": "added bot",
            "role_create": "created role",
            "role_update": "updated role",
            "role_delete": "deleted role",
            "invite_create": "created invite",
            "invite_update": "updated invite",
            "invite_delete": "deleted invite",
            "webhook_create": "created webhook",
            "webhook_update": "updated webhook",
            "webhook_delete": "deleted webhook",
            "emoji_create": "created emoji",
            "emoji_update": "updated emoji",
            "emoji_delete": "deleted emoji",
            "message_delete": "deleted message by",
            "message_bulk_delete": "bulk deleted messages in",
            "message_pin": "pinned message by",
            "message_unpin": "unpinned message by",
            "integration_create": "created integration",
            "integration_update": "updated integration",
            "integration_delete": "deleted integration",
            "sticker_create": "created sticker",
            "sticker_update": "updated sticker",
            "sticker_delete": "deleted sticker",
            "thread_create": "created thread",
            "thread_update": "updated thread",
            "thread_delete": "deleted thread",
        }

    async def is_immune(self, ctx: Context, member: Member) -> bool:
        """
        Check if a specified member or their roles are immune to moderation actions.
        """
        if await self.bot.pool.fetchrow(
            """
            SELECT 1 FROM immune 
            WHERE guild_id = $1 
            AND entity_id = $2 
            AND type = 'user'
            """,
            ctx.guild.id,
            member.id
        ):
            await ctx.embed(
                f"**{member}** is **immune** to moderation actions!",
                message_type="warned"
            )
            return True

        role_ids = [role.id for role in member.roles]
        if await self.bot.pool.fetchrow(
            """
            SELECT * FROM immune 
            WHERE guild_id = $1 
            AND role_id = ANY($2::BIGINT[]) 
            AND type = 'role'
            """,
            ctx.guild.id,
            role_ids
        ):
            await ctx.embed(
                f"One of {member.mention}'s roles is **immune** to moderation actions!",
                message_type="warned"
            )
            return True

        return False

    async def reconfigure_settings(
        self,
        guild: Guild,
        channel: TextChannel | Thread,
        new_channel: TextChannel | Thread,
    ) -> List[str]:
        """
        Update server wide settings for a channel.
        """
        reconfigured: List[str] = []
        config_map = {
            "System Channel": "system_channel",
            "Public Updates Channel": "public_updates_channel",
            "Rules Channel": "rules_channel",
            "AFK Channel": "afk_channel",
        }
        for name, attr in config_map.items():
            value = getattr(channel.guild, attr, None)
            if value == channel:
                await guild.edit(**{attr: new_channel})  # type: ignore
                reconfigured.append(name)

        for table in (
            "logging",
            "gallery",
            "timer.message",
            "timer.purge",
            "sticky_message",
            "welcome_message",
            "goodbye_message",
            "boost_message",
            ("disboard.config", "last_channel_id"),
            "level.notification",
            "commands.disabled",
            "fortnite.rotation",
            "alerts.twitch",
            "feeds.tiktok",
            "feeds.pinterest",
            "feeds.reddit",
        ):
            table_name = table if isinstance(table, str) else table[0]
            column = "channel_id" if isinstance(table, str) else table[1]
            result = await self.bot.pool.execute(
                f"""
                UPDATE {table_name}
                SET {column} = $2
                WHERE {column} = $1
                """,
                channel.id,
                new_channel.id,
            )
            if result != "UPDATE 0":
                pretty_name = (
                    table_name.replace("_", " ")
                    .replace(".", " ")
                    .title()
                    .replace("Feeds Youtube", "YouTube Notifications")
                    .replace("Alerts Twitch", "Twitch Notifications")
                    .replace("Feeds Twitter", "Twitter Notifications")
                    .replace("Feeds Tiktok", "TikTok Notifications")
                    .replace("Feeds Pinterest", "Pinterest Notifications")
                    .replace("Feeds Reddit", "Subreddit Notifications")
                    .replace("Feeds Twitter", "Twitter Notifications")
                )
                reconfigured.append(pretty_name)

        return reconfigured

    def restore_key(self, guild: Guild, member: Member) -> str:
        """
        Generate a Redis key for role restoration.
        """
        return xxh64_hexdigest(f"roles:{guild.id}:{member.id}")

    def forcenick_key(self, guild: Guild, member: Member) -> str:
        """
        Generate a Redis key for forced nicknames.
        """
        return xxh64_hexdigest(f"forcenick:{guild.id}:{member.id}")
    
    def restore_key(self, guild: Guild, member: Member) -> str:
        """
        Generate a Redis key for role restoration.
        """
        return f"restore:{guild.id}:{member.id}"

    @Cog.listener()
    async def on_member_remove(self, member: Member):
        """
        Remove a member's previous roles.
        """
        if member.bot:
            return

        role_ids = [r.id for r in member.roles if r.is_assignable()]
        if role_ids:
            key = self.restore_key(member.guild, member)
            await self.bot.redis.set(key, role_ids, ex=3600)

    @Cog.listener("on_member_join")
    async def restore_roles(self, member: Member):
        """
        Restore a member's previous roles.
        """
        key = self.restore_key(member.guild, member)
        role_ids = cast(
            Optional[List[int]],
            await self.bot.redis.get(key),
        )
        if not role_ids:
            return

        roles = [
            role
            for role_id in role_ids
            if (role := member.guild.get_role(role_id)) is not None
            and role.is_assignable()
            and role not in member.roles
        ]
        if not roles:
            return

        record = await self.bot.pool.fetchrow(
            """
            SELECT
                reassign_roles,
                reassign_ignore_ids
            FROM settings
            WHERE guild_id = $1
            """,
            member.guild.id,
        )
        if not record or not record["reassign_roles"]:
            return

        roles = [role for role in roles if role.id not in record["reassign_ignore_ids"]]
        if not roles:
            return

        await self.bot.redis.delete(key)
        with suppress(HTTPException):
            await member.add_roles(*roles, reason="Restoration of previous roles")
            # log.info(
            #     "Restored %s for %s (%s) in %s (%s).",
            #     format(plural(len(roles)), "role"),
            #     member,
            #     member.id,
            #     member.guild,
            #     member.guild.id,
            # )

    @Cog.listener("on_member_join")
    async def hardban_event(self, member: Member):
        """
        Check if a member is hard banned and ban them if they are.
        """
        hardban = await self.bot.pool.fetchrow(
            """
            SELECT * 
            FROM hardban 
            WHERE guild_id = $1 
            AND user_id = $2
            """,
            member.guild.id,
            member.id,
        )
        if not hardban:
            return

        with suppress(HTTPException):
            await member.ban(reason="User is hard banned")

    @Cog.listener()
    async def on_member_unban(self, guild: Guild, user: User):
        """
        Check if a member is hard banned and ban them if they are.
        """
        hardban = await self.bot.pool.fetchrow(
            """
            SELECT * 
            FROM hardban 
            WHERE guild_id = $1 
            AND user_id = $2
            """,
            guild.id,
            user.id,
        )
        if not hardban:
            return

        with suppress(HTTPException):
            await guild.ban(user, reason="User is hard banned")

    @Cog.listener("on_member_update")
    async def forcenick_event(self, before: Member, after: Member):
        """
        Ensure a user retains their forced nickname.
        """
        record = await self.bot.pool.fetchval(
            """
            SELECT nickname FROM forcenick 
            WHERE guild_id = $1 
            AND user_id = $2
            """,
            before.guild.id,
            before.id,
        )
        if not record or record == after.display_name:
            return

        key = self.forcenick_key(before.guild, before)
        if await self.bot.redis.ratelimited(f"nick:{key}", limit=8, timespan=15):
            await self.bot.pool.execute(
                """
                DELETE FROM forcenick 
                WHERE guild_id = $1 
                AND user_id = $2
                """,
                before.guild.id,
                before.id,
            )
            return

        try:
            await after.edit(nick=record, reason="Forced nickname")
        except HTTPException:
            pass

    @Cog.listener("on_audit_log_entry_member_update")
    async def forcenick_audit(self, entry: AuditLogEntry):
        """
        Remove forced nicknames if a user changes their nickname.
        """
        if (
            not entry.user
            or not entry.target
            or not isinstance(entry.target, Member)
            or not hasattr(entry.after, "nick")
        ):
            return

        if entry.user.bot and entry.user != self.bot.user:
            await self.bot.pool.execute(
                """
                DELETE FROM forcenick 
                WHERE guild_id = $1 
                AND user_id = $2
                """,
                entry.guild.id,
                entry.target.id,
            )

    async def do_removal(
        self,
        ctx: Context,
        amount: int,
        predicate: Callable[[Message], bool] = lambda _: True,
        *,
        before: Optional[Message] = None,
        after: Optional[Message] = None,
    ) -> List[Message]:
        """
        A helper function to do bulk message removal.
        """
        if not ctx.channel.permissions_for(ctx.guild.me).manage_messages:
            raise CommandError("I don't have permission to delete messages!")

        if not before:
            before = ctx.message

        def check(message: Message) -> bool:
            if message.created_at < (utcnow() - timedelta(weeks=2)):
                return False

            elif message.pinned:
                return False

            return predicate(message)

        await quietly_delete(ctx.message)
        messages = await ctx.channel.purge(
            limit=amount,
            check=check,
            before=before,
            after=after,
        )
        if not messages:
            raise CommandError("No messages were found, try a larger search?")

        return messages

    @hybrid_command(aliases=["bc"], examples="100")
    @has_permissions(manage_messages=True)
    async def cleanup(
        self,
        ctx: Context,
        amount: Annotated[
            int,
            Range[int, 1, 1000],
        ] = 100,
    ):
        """
        Remove bot invocations and messages from bots.
        """
        await self.do_removal(
            ctx,
            amount,
            lambda message: (
                message.author.bot
                or message.content.startswith(
                    (ctx.clean_prefix, ",", ";", ".", "!", "$")
                )
            ),
        )

    @group(
        aliases=["prune", "rm", "c"],
        invoke_without_command=True,
        example="@x 100"
    )
    @max_concurrency(1, BucketType.channel)
    @has_permissions(manage_messages=True)
    async def purge(
        self,
        ctx: Context,
        user: Optional[
            Annotated[
                Member,
                StrictMember,
            ]
            | Annotated[
                User,
                StrictUser,
            ]
        ],
        amount: Annotated[
            int,
            Range[int, 1, 1000],
        ],
    ):
        """
        Remove messages which meet a criteria.
        """
        await self.do_removal(
            ctx,
            amount,
            lambda message: message.author == user if user else True,
        )

    @purge.command(
        name="embeds",
        aliases=["embed"],
        example="100"
    )
    @has_permissions(manage_messages=True)
    async def purge_embeds(
        self,
        ctx: Context,
        amount: Annotated[
            int,
            Range[int, 1, 1000],
        ] = 100,
    ):
        """
        Remove messages which have embeds.
        """
        await self.do_removal(
            ctx,
            amount,
            lambda message: bool(message.embeds),
        )

    @purge.command(
        name="files",
        aliases=["file"],
        example="100"
    )
    @has_permissions(manage_messages=True)
    async def purge_files(
        self,
        ctx: Context,
        amount: Annotated[
            int,
            Range[int, 1, 1000],
        ] = 100,
    ):
        """
        Remove messages which have files.
        """
        await self.do_removal(
            ctx,
            amount,
            lambda message: bool(message.attachments),
        )

    @purge.command(
        name="images",
        aliases=["image"],
        example="100"
    )
    @has_permissions(manage_messages=True)
    async def purge_images(
        self,
        ctx: Context,
        amount: Annotated[
            int,
            Range[int, 1, 1000],
        ] = 100,
    ):
        """
        Remove messages which have images.
        """
        await self.do_removal(
            ctx,
            amount,
            lambda message: bool(message.attachments or message.embeds),
        )

    @purge.command(
        name="stickers",
        aliases=["sticker"],
        example="100"
    )
    @has_permissions(manage_messages=True)
    async def purge_stickers(
        self,
        ctx: Context,
        amount: Annotated[
            int,
            Range[int, 1, 1000],
        ] = 100,
    ):
        """
        Remove messages which have stickers.
        """
        await self.do_removal(
            ctx,
            amount,
            lambda message: bool(message.stickers),
        )

    @purge.command(
        name="voice",
        aliases=["vm"],
        example="100"
    )
    @has_permissions(manage_messages=True)
    async def purge_voice(
        self,
        ctx: Context,
        amount: Annotated[
            int,
            Range[int, 1, 1000],
        ] = 100,
    ):
        """
        Remove voice messages.
        """
        await self.do_removal(
            ctx,
            amount,
            lambda message: any(
                attachment.waveform for attachment in message.attachments
            ),
        )

    @purge.command(
        name="system",
        aliases=["sys"],
        example="100"
    )
    @has_permissions(manage_messages=True)
    async def purge_system(
        self,
        ctx: Context,
        amount: Annotated[
            int,
            Range[int, 1, 1000],
        ] = 100,
    ):
        """
        Remove system messages.
        """
        await self.do_removal(
            ctx, 
            amount, 
            lambda message: message.is_system()
        )

    @purge.command(
        name="mentions",
        aliases=["mention"],
        example="100"
    )
    @has_permissions(manage_messages=True)
    async def purge_mentions(
        self,
        ctx: Context,
        amount: Annotated[
            int,
            Range[int, 1, 1000],
        ] = 100,
    ):
        """
        Remove messages which have mentions.
        """
        await self.do_removal(
            ctx,
            amount,
            lambda message: bool(message.mentions),
        )

    @purge.command(
        name="emojis",
        aliases=[
            "emotes",
            "emoji",
            "emote",
        ],
        example="100"
    )
    @has_permissions(manage_messages=True)
    async def purge_emojis(
        self,
        ctx: Context,
        amount: Annotated[
            int,
            Range[int, 1, 1000],
        ] = 100,
    ):
        """
        Remove messages which have custom emojis.
        """
        custom_emoji = re.compile(r"<a?:[a-zA-Z0-9\_]+:([0-9]+)>")

        await self.do_removal(
            ctx,
            amount,
            lambda message: bool(message.content)
            and bool(custom_emoji.search(message.content)),
        )

    @purge.command(
        name="invites",
        aliases=[
            "invite",
            "inv",
        ],
        example="100"
    )
    @has_permissions(manage_messages=True)
    async def purge_invites(
        self,
        ctx: Context,
        amount: Annotated[
            int,
            Range[int, 1, 1000],
        ] = 100,
    ):
        """
        Remove messages which have invites.
        """
        invite_link = re.compile(
            r"(?:https?://)?discord(?:\.gg|app\.com/invite)/[a-zA-Z0-9]+/?"
        )

        await self.do_removal(
            ctx,
            amount,
            lambda message: bool(message.content)
            and bool(invite_link.search(message.content)),
        )

    @purge.command(
        name="links",
        aliases=["link"],
        example="100"
    )
    @has_permissions(manage_messages=True)
    async def purge_links(
        self,
        ctx: Context,
        amount: Annotated[
            int,
            Range[int, 1, 1000],
        ] = 100,
    ):
        """
        Remove messages which have links.
        """
        await self.do_removal(
            ctx,
            amount,
            lambda message: bool(message.content) and "http" in message.content.lower(),
        )

    @purge.command(
        name="contains",
        aliases=["contain"],
        example="xx 100"
    )
    @has_permissions(manage_messages=True)
    async def purge_contains(
        self,
        ctx: Context,
        substring: Annotated[
            str,
            Range[str, 2],
        ],
        amount: Annotated[
            int,
            Range[int, 1, 1000],
        ] = 100,
    ):
        """
        Remove messages which contain a substring.

        The substring must be at least 3 characters long.
        """
        await self.do_removal(
            ctx,
            amount,
            lambda message: bool(message.content)
            and substring.lower() in message.content.lower(),
        )

    @purge.command(
        name="startswith",
        aliases=[
            "prefix",
            "start",
            "sw",
        ],
    )
    @has_permissions(manage_messages=True)
    async def purge_startswith(
        self,
        ctx: Context,
        substring: Annotated[
            str,
            Range[str, 3],
        ],
        amount: Annotated[
            int,
            Range[int, 1, 1000],
        ] = 100,
    ):
        """
        Remove messages which start with a substring.

        The substring must be at least 3 characters long.
        """
        await self.do_removal(
            ctx,
            amount,
            lambda message: bool(message.content)
            and message.content.lower().startswith(substring.lower()),
        )

    @purge.command(
        name="endswith",
        aliases=[
            "suffix",
            "end",
            "ew",
        ],
    )
    @has_permissions(manage_messages=True)
    async def purge_endswith(
        self,
        ctx: Context,
        substring: Annotated[
            str,
            Range[str, 3],
        ],
        amount: Annotated[
            int,
            Range[int, 1, 1000],
        ] = 100,
    ):
        """
        Remove messages which end with a substring.

        The substring must be at least 3 characters long.
        """
        await self.do_removal(
            ctx,
            amount,
            lambda message: bool(message.content)
            and message.content.lower().endswith(substring.lower()),
        )

    @purge.command(
        name="humans",
        aliases=["human"],
    )
    @has_permissions(manage_messages=True)
    async def purge_humans(
        self,
        ctx: Context,
        amount: Annotated[
            int,
            Range[int, 1, 1000],
        ] = 100,
    ):
        """
        Remove messages which are not from a bot.
        """
        await self.do_removal(
            ctx,
            amount,
            lambda message: not message.author.bot,
        )

    @purge.command(
        name="bots",
        aliases=["bot"]
    )
    @has_permissions(manage_messages=True)
    async def purge_bots(
        self,
        ctx: Context,
        amount: Annotated[
            int,
            Range[int, 1, 1000],
        ] = 100,
    ):
        """
        Remove messages which are from a bot.
        """
        await self.do_removal(
            ctx,
            amount,
            lambda message: message.author.bot,
        )

    @purge.command(
        name="webhooks",
        aliases=["webhook"],
    )
    @has_permissions(manage_messages=True)
    async def purge_webhooks(
        self,
        ctx: Context,
        amount: Annotated[
            int,
            Range[int, 1, 1000],
        ] = 100,
    ):
        """
        Remove messages which are from a webhook.
        """
        await self.do_removal(
            ctx,
            amount,
            lambda message: bool(message.webhook_id),
        )

    @purge.command(name="before")
    @has_permissions(manage_messages=True)
    async def purge_before(
        self,
        ctx: Context,
        message: Optional[Message],
    ):
        """
        Remove messages before a target message.
        """
        message = message or ctx.replied_message
        if not message:
            return await ctx.send_help(ctx.command)

        if message.channel != ctx.channel:
            return await ctx.send_help(ctx.command)

        await self.do_removal(
            ctx,
            300,
            before=message,
        )

    @purge.command(
        name="after",
        aliases=["upto", "up"],
    )
    @has_permissions(manage_messages=True)
    async def purge_after(
        self,
        ctx: Context,
        message: Optional[Message],
    ):
        """
        Remove messages after a target message.
        """
        message = message or ctx.replied_message
        if not message:
            return await ctx.send_help(ctx.command)

        if message.channel != ctx.channel:
            return await ctx.send_help(ctx.command)

        await self.do_removal(
            ctx,
            300,
            after=message,
        )

    @purge.command(name="between")
    @has_permissions(manage_messages=True)
    async def purge_between(
        self,
        ctx: Context,
        start: Message,
        finish: Message,
    ):
        """
        Remove messages between two messages.
        """
        if start.channel != ctx.channel or finish.channel != ctx.channel:
            return await ctx.send_help(ctx.command)

        await self.do_removal(
            ctx,
            2000,
            after=start,
            before=finish,
        )

    @purge.command(
        name="except",
        aliases=[
            "besides",
            "schizo",
        ],
    )
    @has_permissions(manage_messages=True)
    async def purge_except(
        self,
        ctx: Context,
        member: Member,
        amount: Annotated[
            int,
            Range[int, 1, 1000],
        ] = 500,
    ):
        """
        Remove messages not sent by a member.
        """
        await self.do_removal(
            ctx, 
            amount, 
            lambda message: message.author != member
        )

    @purge.command(
        name="reactions",
        aliases=["reaction", "react"],
    )
    @has_permissions(manage_messages=True)
    @max_concurrency(1, BucketType.channel)
    async def purge_reactions(
        self,
        ctx: Context,
        amount: Annotated[
            int,
            Range[int, 1, 1000],
        ] = 100,
    ):
        """
        Remove reactions from messages.

        This command is by no means quick,
        therefore it will take a while to complete.
        """
        total_removed: int = 0
        async with ctx.typing():
            async for message in ctx.channel.history(limit=amount, before=ctx.message):
                if len(message.reactions):
                    total_removed += sum(
                        reaction.count for reaction in message.reactions
                    )
                    await message.clear_reactions()

        return await ctx.approve(
            f"Successfully  removed {plural(total_removed, md='`'):reaction}"
        )

    async def do_mass_role(
        self,
        ctx: Context,
        role: Role,
        predicate: Callable[[Member], bool] = lambda _: True,
        *,
        action: Literal["add", "remove"] = "add",
        failure_message: Optional[str] = None,
    ) -> Message:
        """
        A helper method to mass add or remove a role from members.
        """
        if not failure_message:
            failure_message = (
                f"Everyone you can manage already has {role.mention}!"
                if action == "add"
                else f"Nobody you can manage has {role.mention}!"
            )

        if not ctx.guild.chunked:
            await ctx.guild.chunk(cache=True)

        members = []
        for member in ctx.guild.members:
            if not predicate(member):
                continue

            if (role in member.roles) == (action == "add"):
                continue

            try:
                await TouchableMember(allow_author=True).check(ctx, member)
            except BadArgument:
                continue

            members.append(member)

        if not members:
            return await ctx.warn(failure_message)

        word = "to" if action == "add" else "from"

        pending_message = await ctx.neutral(
            f"Starting to **{action}** {role.mention} "
            f"{word} {plural(len(members), md='`'):member}...",
            f"This will take around **{format_timespan(len(members))}**",
        )

        failed: List[Member] = []
        try:
            async with ctx.typing():
                for member in members:
                    try:
                        if action == "add":
                            await member.add_roles(
                                role,
                                reason=f"Mass role {action} by {ctx.author}",
                            )
                        else:
                            await member.remove_roles(
                                role,
                                reason=f"Mass role {action} by {ctx.author}",
                            )

                    except HTTPException:
                        failed.append(member)
                        if len(failed) >= 10:
                            break

        finally:
            await quietly_delete(pending_message)

        result = [
            f"{action.title()[:5]}ed {role.mention} {word} {plural(len(members) - len(failed), md='`'):member}"
        ]
        if failed:
            result.append(
                f"Failed {action[:5]}ing {role.mention} {word} {plural(len(failed), md='`'):member}: {', '.join(member.mention for member in failed)}"
            )

        return await ctx.approve(*result)

    @group(
        aliases=["r"],
        invoke_without_command=True,
        example="@x @member"
    )
    @has_permissions(manage_roles=True)
    async def role(
        self,
        ctx: Context,
        member: Annotated[
            Member,
            TouchableMember(
                allow_author=True,
            ),
        ],
        *,
        role: GoodRole,
    ) -> Message:
        """
        Add or remove a role from a member.
        """
        # if await self.is_immune(ctx, member):
        #     return

        if role in member.roles:
            return await ctx.invoke(self.role_remove, member=member, role=role)

        return await ctx.invoke(self.role_add, member=member, role=role)

    @role.command(
        name="add",
        aliases=["grant"],
        example="@x @member"
    )
    @has_permissions(manage_roles=True)
    async def role_add(
        self,
        ctx: Context,
        member: Annotated[
            Member,
            TouchableMember(
                allow_author=True,
            ),
        ],
        *,
        role: GoodRole,
    ) -> Message:
        """
        Add a role to a member.
        """
        if role in member.roles:
            return await ctx.embed(
                f"{member.mention} already has {role.mention}!",
                message_type="warned"
            )

        if await self.is_immune(ctx, member):
            return

        reason = f"Added by {ctx.author.name} ({ctx.author.id})"

        await member.add_roles(role, reason=reason)

        # try:
        #     await ModConfig.sendlogs(self.bot, "role add", ctx.author, member, reason)  # type: ignore
        # except:
        #     pass

        return await ctx.embed(
            f"Added {role.mention} to {member.mention}",
            message_type="approved"
        )

    @role.command(
        name="remove",
        aliases=["rm"],
        example="@x @staff"
    )
    @has_permissions(manage_roles=True)
    async def role_remove(
        self,
        ctx: Context,
        member: Annotated[
            Member,
            TouchableMember(
                allow_author=True,
            ),
        ],
        *,
        role: GoodRole,
    ) -> Message:
        """
        Remove a role from a member.
        """
        if role not in member.roles:
            return await ctx.embed(
                f"{member.mention} doesn't have {role.mention}!",
                message_type="warned"
            )

        if await self.is_immune(ctx, member):
            return

        reason = f"Removed by {ctx.author.name} ({ctx.author.id})"
        await member.remove_roles(role, reason=reason)

        # try:
        #     await ModConfig.sendlogs(self.bot, "role remove", ctx.author, member, reason)  # type: ignore
        # except:
        #     pass

        return await ctx.embed(
            f"Removed {role.mention} from {member.mention}",
            message_type="approved"
        )

    @role.command(
        name="restore",
        aliases=["re"],
        example="@x"
    )
    @has_permissions(manage_roles=True)
    async def role_restore(
        self,
        ctx: Context,
        member: Annotated[
            Member,
            TouchableMember,
        ],
    ) -> Message:
        """
        Restore a member's previous roles.
        """
        key = self.restore_key(ctx.guild, member)
        role_ids = cast(
            Optional[List[int]],
            await self.bot.redis.getdel(key),
        )
        if not role_ids:
            return await ctx.embed(
                f"No roles to restore for {member.mention}!",
                message_type="warned"
            )

        roles = [
            role
            for role_id in role_ids
            if (role := ctx.guild.get_role(role_id)) is not None
            and role.is_assignable()
            and role not in member.roles
            and await StrictRole().check(ctx, role)
        ]
        if not roles:
            return await ctx.embed(
                f"{member.mention} doesn't have any previous roles!",
                message_type="warned"
            )

        # try:
        #     await ModConfig.sendlogs(
        #         self.bot, "role restore", ctx.author, member, "No reason provided"
        #     )  # type: ignore
        # except:
        #     pass

        await member.add_roles(
            *roles,
            reason=f"Restoration of previous roles by {ctx.author.name} ({ctx.author.id})",
        )
        return await ctx.embed(
            f"Restored {human_join([role.mention for role in roles], final='and')} to {member.mention}",
            message_type="approved"
        )

    @role.command(
        name="create",
        aliases=["make"],
        example="#ff0000 true staff"
    )
    @has_permissions(manage_roles=True)
    async def role_create(
        self,
        ctx: Context,
        color: Optional[ColorConverter] = None,
        hoist: Optional[bool] = None,
        *,
        name: Range[str, 1, 100],
    ) -> Message:
        """
        Create a role.
        """
        if len(ctx.guild.roles) >= 250:
            return await ctx.embed(
                "This server has too many roles! (`250`)",
                message_type="warned"
            )

        config = await Settings.fetch(self.bot, ctx.guild)
        if (
            config
            and config.role
            and not config.is_whitelisted(ctx.author)
            and await config.check_threshold(self.bot, ctx.author, "role")
        ):
            await strip_roles(
                ctx.author,
                dangerous=True,
                reason="Antinuke role threshold reached",
            )
            return await ctx.embed(
                "You've exceeded the antinuke threshold for **role creation**!",
                "Your **administrative permissions** have been revoked",
                message_type="warned"
            )

        reason = f"Created by {ctx.author.name} ({ctx.author.id})"
        role = await ctx.guild.create_role(
            name=name,
            color=color or Color.default(),
            hoist=hoist or False,
            reason=reason,
        )

        return await ctx.embed(
            f"Successfully created {role.mention}",
            message_type="approved"
        )

    @role.command(
        name="delete",
        aliases=["del"],
        example="@bots"
    )
    @has_permissions(manage_roles=True)
    async def role_delete(
        self,
        ctx: Context,
        *,
        role: Annotated[
            Role,
            StrictRole,
        ],
    ) -> Optional[Message]:
        """
        Delete a role.
        """
        if role.members:
            await ctx.prompt(
                f"{role.mention} has {plural(len(role.members), md='`'):member}, are you sure you want to delete it?",
            )

        config = await Settings.fetch(self.bot, ctx.guild)
        if (
            config
            and config.role
            and not config.is_whitelisted(ctx.author)
            and await config.check_threshold(self.bot, ctx.author, "role")
        ):
            await strip_roles(
                ctx.author,
                dangerous=True,
                reason="Antinuke role threshold reached",
            )
            return await ctx.embed(
                "You've exceeded the antinuke threshold for **role deletion**!",
                "Your **administrative permissions** have been revoked",
                message_type="warned"
            )

        await role.delete()
        return await ctx.embed(
            f"Successfully deleted **{role.name}**", 
            message_type="approved"
        )

    @role.command(
        name="color",
        aliases=["colour"],
    )
    @has_permissions(manage_roles=True)
    async def role_color(
        self,
        ctx: Context,
        role: Annotated[
            Role,
            StrictRole(
                check_integrated=False,
            ),
        ],
        *,
        color: Color,
    ) -> Message:
        """
        Change a role's color.
        """
        reason = f"Changed by {ctx.author.name} ({ctx.author.id})"
        await role.edit(color=color, reason=reason)
        return await ctx.embed(
            f"Changed {role.mention}'s color to `{color}`",
            message_type="approved"
        )

    @role.command(name="rename", aliases=["name"], example="@member humans")
    @has_permissions(manage_roles=True)
    async def role_rename(
        self,
        ctx: Context,
        role: Annotated[
            Role,
            StrictRole(
                check_integrated=False,
            ),
        ],
        *,
        name: Range[str, 1, 100],
    ) -> None:
        """
        Change a role's name.
        """
        reason = f"Changed by {ctx.author.name} ({ctx.author.id})"
        await role.edit(name=name, reason=reason)
        return await ctx.embed(
            f"Changed {role.mention}'s name to `{name}`", 
            message_type="approved"
        )

    @role.command(name="hoist", example="@staff")
    @has_permissions(manage_roles=True)
    async def role_hoist(
        self,
        ctx: Context,
        *,
        role: Annotated[
            Role,
            StrictRole(
                check_integrated=False,
            ),
        ],
    ) -> Message:
        """
        Toggle if a role should appear in the sidebar.
        """
        reason = f"Changed by {ctx.author.name} ({ctx.author.id})"
        await role.edit(hoist=not role.hoist, reason=reason)
        return await ctx.embed(
            f"{role.mention} is {'now' if role.hoist else 'no longer'} hoisted",
            message_type="approved"
        )

    @role.command(name="mentionable", example="@staff")
    @has_permissions(manage_roles=True)
    async def role_mentionable(
        self,
        ctx: Context,
        *,
        role: Annotated[
            Role,
            StrictRole(
                check_integrated=False,
            ),
        ],
    ) -> Message:
        """
        Toggle if a role should be mentionable.
        """
        reason = f"Changed by {ctx.author.name} ({ctx.author.id})"
        await role.edit(mentionable=not role.mentionable, reason=reason)
        return await ctx.embed(
            f"{role.mention} is {'now' if role.mentionable else 'no longer'} mentionable",
            message_type="approved"
        )

    @role.command(name="icon", example="@member https://example.com/image.png")
    @has_permissions(manage_roles=True)
    async def role_icon(
        self,
        ctx: Context,
        role: Annotated[
            Role,
            StrictRole(
                check_integrated=False,
            ),
        ],
        icon: PartialEmoji | PartialAttachment | str = parameter(
            default=PartialAttachment.fallback,
        ),
    ) -> Message:
        """
        Change a role's icon.
        """
        if ctx.guild.premium_tier < 2:
            return await ctx.embed(
            "Role icons are only available for **level 2** boosted servers!",
            message_type="warned"
        )

        reason = f"Changed by {ctx.author.name} ({ctx.author.id})"
        if isinstance(icon, str) and icon in ("none", "remove", "delete"):
            if not role.display_icon:
                return await ctx.embed(
                    f"{role.mention} doesn't have an icon!",
                    message_type="warned"
                )

            await role.edit(display_icon=None, reason=reason)
            return await ctx.embed(
            f"Removed {role.mention}'s icon",
            message_type="approved"
        )

        buffer: bytes | str
        processing: Optional[Message] = None

        if isinstance(icon, str):
            buffer = icon
        elif isinstance(icon, PartialEmoji):
            buffer = await icon.read()
            if icon.animated:
                processing = await ctx.embed(
                    "Converting animated emoji to a static image...",
                    message_type="neutral"
            )
                buffer = await convert_image(buffer, "png")

        elif icon.is_gif():
            processing = await ctx.embed(
            "Converting GIF to a static image...",
            message_type="neutral"
        )
            buffer = await convert_image(icon.buffer, "png")

        elif not icon.is_image():
            return await ctx.embed(
            "The attachment must be an image!",
            message_type="warned"
        )

        else:
            buffer = icon.buffer

        if processing:
            await processing.delete(delay=0.5)

        await role.edit(
            display_icon=buffer,
            reason=reason,
        )
        return await ctx.embed(
            f"Changed {role.mention}'s icon to "
            + (
            f"[**image**]({icon.url})"
            if isinstance(icon, PartialAttachment)
            else f"**{icon}**"
            ),
            message_type="approved"
        )

    @role.group(
        name="all",
        aliases=["everyone"],
        invoke_without_command=True,
        max_concurrency=MASS_ROLE_CONCURRENCY,
        example="@member"
    )
    @has_permissions(manage_roles=True)
    async def role_all(
        self,
        ctx: Context,
        *,
        role: Annotated[
            Role,
            StrictRole,
        ],
    ) -> Message:
        """
        Add a role to everyone.
        """
        return await self.do_mass_role(ctx, role)

    @role_all.command(
        name="remove",
        aliases=["rm"],
        max_concurrency=MASS_ROLE_CONCURRENCY,
        example="@admin"
    )
    @has_permissions(manage_roles=True)
    async def role_all_remove(
        self,
        ctx: Context,
        *,
        role: Annotated[
            Role,
            StrictRole,
        ],
    ) -> Message:
        """
        Remove a role from everyone.
        """
        return await self.do_mass_role(
            ctx,
            role,
            action="remove",
        )

    @role.group(
        name="humans",
        invoke_without_command=True,
        max_concurrency=MASS_ROLE_CONCURRENCY,
        example="@member"
    )
    @has_permissions(manage_roles=True)
    async def role_humans(
        self,
        ctx: Context,
        *,
        role: Annotated[
            Role,
            StrictRole,
        ],
    ) -> Message:
        """
        Add a role to all humans.
        """
        return await self.do_mass_role(
            ctx,
            role,
            lambda member: not member.bot,
        )

    @role_humans.command(
        name="remove",
        aliases=["rm"],
        max_concurrency=MASS_ROLE_CONCURRENCY,
        example="@bots"
    )
    @has_permissions(manage_roles=True)
    async def role_humans_remove(
        self,
        ctx: Context,
        *,
        role: Annotated[
            Role,
            StrictRole,
        ],
    ) -> Message:
        """
        Remove a role from all humans.
        """
        return await self.do_mass_role(
            ctx,
            role,
            lambda member: not member.bot,
            action="remove",
        )

    @role.group(
        name="bots",
        invoke_without_command=True,
        max_concurrency=MASS_ROLE_CONCURRENCY,
        example="@bots"
    )
    @has_permissions(manage_roles=True)
    async def role_bots(
        self,
        ctx: Context,
        *,
        role: Annotated[
            Role,
            StrictRole,
        ],
    ) -> Message:
        """
        Add a role to all bots.
        """
        return await self.do_mass_role(
            ctx,
            role,
            lambda member: member.bot,
        )

    @role_bots.command(
        name="remove",
        aliases=["rm"],
        max_concurrency=MASS_ROLE_CONCURRENCY,
        example="@member"
    )
    @has_permissions(manage_roles=True)
    async def role_bots_remove(
        self,
        ctx: Context,
        *,
        role: Annotated[
            Role,
            StrictRole,
        ],
    ) -> Message:
        """
        Remove a role from all bots.
        """
        return await self.do_mass_role(
            ctx,
            role,
            lambda member: member.bot,
            action="remove",
        )

    @role.group(
        name="has",
        aliases=["with", "in"],
        invoke_without_command=True,
        max_concurrency=MASS_ROLE_CONCURRENCY,
        example="@muted @member"
    )
    @has_permissions(manage_roles=True)
    async def role_has(
        self,
        ctx: Context,
        role: Annotated[
            Role,
            StrictRole(
                check_integrated=False,
            ),
        ],
        *,
        assign_role: Annotated[
            Role,
            StrictRole,
        ],
    ) -> Message:
        """
        Add a role to everyone with a role.
        """
        return await self.do_mass_role(
            ctx,
            assign_role,
            lambda member: role in member.roles,
        )

    @role_has.command(
        name="remove",
        aliases=["rm"],
        max_concurrency=MASS_ROLE_CONCURRENCY,
        example="@muted @member"
    )
    @has_permissions(manage_roles=True)
    async def role_has_remove(
        self,
        ctx: Context,
        role: Annotated[
            Role,
            StrictRole(
                check_integrated=False,
            ),
        ],
        *,
        remove_role: Annotated[
            Role,
            StrictRole,
        ],
    ) -> Message:
        """
        Remove a role from everyone with a role.
        """
        return await self.do_mass_role(
            ctx,
            remove_role,
            lambda member: role in member.roles,
            action="remove",
        )

    @hybrid_group(
        aliases=["lock"],
        invoke_without_command=True,
        example="#general idk why",
    )
    @has_permissions(manage_roles=True)
    async def lockdown(
        self,
        ctx: Context,
        channel: Optional[TextChannel | Thread],
        *,
        reason: str = "No reason provided",
    ) -> Message:
        """
        Prevent members from sending messages.
        """
        channel = cast(TextChannel | Thread, channel or ctx.channel)
        lock_role = ctx.guild.get_role(ctx.settings.lock_role_id) or ctx.guild.default_role

        if (
            isinstance(channel, Thread)
            and channel.locked
            or isinstance(channel, TextChannel)
            and channel.overwrites_for(lock_role).send_messages is False 
        ):
            return await ctx.embed(
                f"{channel.mention} is already locked!",
                message_type="warned"
            )

        if isinstance(channel, Thread):
            await channel.edit(
                locked=True,
                reason=f"{ctx.author.name} / {reason}",
            )
        else:
            overwrite = channel.overwrites_for(lock_role)
            overwrite.send_messages = False
            await channel.set_permissions(
                lock_role,
                overwrite=overwrite,
                reason=f"{ctx.author.name} / {reason}",
            )

        return await ctx.embed(
            f"Successfully locked down {channel.mention}",
            message_type="approved"
        )

    @lockdown.command(name="all", example="idk why")
    @has_permissions(manage_roles=True)
    @max_concurrency(1, BucketType.guild)
    @cooldown(1, 30, BucketType.guild)
    async def lockdown_all(
        self,
        ctx: Context,
        *,
        reason: str = "No reason provided",
    ) -> Message:
        """
        Prevent members from sending messages in all channels.
        """

        if not ctx.settings.lock_ignore:
            await ctx.prompt(
                "Are you sure you want to lock **ALL** channels?\n",
                "-# You haven't ignored any important channels yet",
            )

        initial_message = await ctx.embed(
            "Locking down all channels...",
            message_type="neutral"
        )
        async with ctx.typing():
            start = perf_counter()
            for channel in ctx.guild.text_channels:
                if (
                    channel.overwrites_for(ctx.settings.lock_role).send_messages
                    is False
                    or channel in ctx.settings.lock_ignore
                ):
                    continue

                overwrite = channel.overwrites_for(ctx.settings.lock_role)
                overwrite.send_messages = False
                await channel.set_permissions(
                    ctx.settings.lock_role,
                    overwrite=overwrite,
                    reason=f"{ctx.author.name} / {reason} (SERVER LOCKDOWN)",
                )

        return await ctx.embed(
            f"Successfully locked down {plural(len(ctx.guild.text_channels) - len(ctx.settings.lock_ignore), md='`'):channel} in `{perf_counter() - start:.2f}s`",
            message_type="approved",
            edit=initial_message,
        )

    @lockdown.command(name="role", example="@Muted")
    @has_permissions(manage_roles=True)
    async def lockdown_role(
        self,
        ctx: Context,
        *,
        role: Annotated[
            Role,
            StrictRole(
                check_integrated=False,
                allow_default=True,
            ),
        ],
    ) -> Message:
        """
        Set the role which will be locked from sending messages.
        """
        await ctx.settings.update(lock_role_id=role.id)
        return await ctx.embed(f"Now locking {role.mention} from sending messages", message_type="approved")

    @lockdown.group(
        name="ignore",
        aliases=["exempt"],
        invoke_without_command=True,
        example="#announcements"
    )
    @has_permissions(manage_roles=True)
    async def lockdown_ignore(
        self,
        ctx: Context,
        *,
        channel: TextChannel,
    ) -> Message:
        """
        Ignore a channel from being unintentionally locked.
        """

        if channel in ctx.settings.lock_ignore:
            return await ctx.embed(
            f"{channel.mention} is already being ignored!",
            message_type="warned"
            )

        ctx.settings.lock_ignore_ids.append(channel.id)
        await ctx.settings.update()
        return await ctx.embed(
            f"Now ignoring {channel.mention} from lockdown",
            message_type="approved"
        )

    @lockdown_ignore.command(
        name="remove",
        aliases=["delete", "del", "rm"],
        example="#announcements"
    )
    @has_permissions(manage_roles=True)
    async def lockdown_ignore_remove(
        self,
        ctx: Context,
        *,
        channel: TextChannel,
    ) -> Message:
        """
        Remove a channel from being ignored.
        """

        if channel not in ctx.settings.lock_ignore:
            return await ctx.embed(
            f"{channel.mention} isn't being ignored!",
            message_type="warned"
        )

        ctx.settings.lock_ignore_ids.remove(channel.id)
        await ctx.settings.update()
        return await ctx.embed(
            f"No longer ignoring {channel.mention} from lockdown",
            message_type="approved"
        )

    @lockdown_ignore.command(
        name="list",
        aliases=["ls"],
    )
    @has_permissions(manage_roles=True)
    async def lockdown_ignore_list(self, ctx: Context) -> Message:
        """
        View all channels being ignored.
        """

        if not ctx.settings.lock_ignore:
            return await ctx.warn("No channels are being ignored!")

        entries=[
            f"{channel.mention} (`{channel.id}`)"
            for channel in ctx.settings.lock_ignore
        ],
        
        return await ctx.paginate(
            entries=entries, 
            embed=Embed(title=f"{len(entries)} Ignored Channel{'s' if len(entries) != 1 else ''}")
        )

    @hybrid_group(
        aliases=["unlock"],
        invoke_without_command=True,
        example="#general idk why",
    )
    @has_permissions(manage_roles=True)
    async def unlockdown(
        self,
        ctx: Context,
        channel: Optional[TextChannel | Thread],
        *,
        reason: str = "No reason provided",
    ) -> Message:
        """
        Allow members to send messages.
        """
        channel = cast(TextChannel | Thread, channel or ctx.channel)
        if not isinstance(channel, (TextChannel | Thread)):
            return await ctx.embed(
                "You can only unlock text channels!", 
                message_type="warned"
            )

        if (
            isinstance(channel, Thread)
            and not channel.locked
            or isinstance(channel, TextChannel)
            and channel.overwrites_for(ctx.settings.lock_role).send_messages is True
        ):
            return await ctx.embed(
                f"{channel.mention} is already unlocked!", 
                message_type="warned"
            )

        if isinstance(channel, Thread):
            await channel.edit(
            locked=False,
            reason=f"{ctx.author.name} / {reason}",
            )
        else:
            overwrite = channel.overwrites_for(ctx.settings.lock_role)
            overwrite.send_messages = True
            await channel.set_permissions(
            ctx.settings.lock_role,
            overwrite=overwrite,
            reason=f"{ctx.author.name} / {reason}",
            )

        return await ctx.embed(
            f"Successfully unlocked {channel.mention}", 
            message_type="approved"
        )

    @unlockdown.command(name="all", example="idk why")
    @has_permissions(manage_roles=True)
    @max_concurrency(1, BucketType.guild)
    @cooldown(1, 30, BucketType.guild)
    async def unlockdown_all(
        self,
        ctx: Context,
        *,
        reason: str = "No reason provided",
    ) -> Message:
        """
        Allow members to send messages in all channels.
        """
        if not ctx.settings.lock_ignore:
            await ctx.prompt(
            "Are you sure you want to unlock **ALL** channels?",
            "You haven't ignored any important channels yet",
            )

        initial_message = await ctx.embed(
            "Unlocking all channels...",
            message_type="neutral"
        )
        async with ctx.typing():
            start = perf_counter()
            for channel in ctx.guild.text_channels:
                if (
                    channel.overwrites_for(ctx.settings.lock_role).send_messages is True
                    or channel in ctx.settings.lock_ignore
                ):
                    continue

            overwrite = channel.overwrites_for(ctx.settings.lock_role)
            overwrite.send_messages = True
            await channel.set_permissions(
                ctx.settings.lock_role,
                overwrite=overwrite,
                reason=f"{ctx.author.name} / {reason} (SERVER UNLOCKDOWN)",
            )

        return await ctx.embed(
            f"Successfully unlocked {plural(len(ctx.guild.text_channels) - len(ctx.settings.lock_ignore), md='`'):channel} in `{perf_counter() - start:.2f}s`",
            message_type="approved",
            edit=initial_message,
        )

    @hybrid_command(aliases=["private", "priv"], example="#general idk why")
    @has_permissions(manage_roles=True)
    async def hide(
        self,
        ctx: Context,
        channel: Optional[TextChannel | VoiceChannel],
        target: Optional[Member | Role],
        *,
        reason: str = "No reason provided",
    ) -> Message:
        """
        Hide a channel from a member or role.
        """
        channel = cast(TextChannel, channel or ctx.channel)
        if not isinstance(channel, (TextChannel, VoiceChannel)):
            return await ctx.embed("You can only hide text & voice channels!", message_type="warned")

        target = target or ctx.settings.lock_role

        if channel.overwrites_for(target).read_messages is False:
            return await ctx.embed(
            f"{channel.mention} is already hidden for {target.mention}!"
            if target != ctx.settings.lock_role
            else f"{channel.mention} is already hidden!",
            message_type="warned"
            )

        overwrite = channel.overwrites_for(target)
        overwrite.read_messages = False
        await channel.set_permissions(
            target,
            overwrite=overwrite,
            reason=f"{ctx.author.name} / {reason}",
        )

        return await ctx.embed(
            f"{channel.mention} is now hidden for {target.mention}"
            if target != ctx.settings.lock_role
            else f"{channel.mention} is now hidden",
            message_type="approved"
        )

    @hybrid_command(aliases=["unhide", "public"], example="#general")
    @has_permissions(manage_roles=True)
    async def reveal(
        self,
        ctx: Context,
        channel: Optional[TextChannel | VoiceChannel],
        target: Optional[Member | Role],
        *,
        reason: str = "No reason provided",
    ) -> Message:
        """
        Reveal a channel to a member or role.
        """
        channel = cast(TextChannel, channel or ctx.channel)
        if not isinstance(channel, (TextChannel, VoiceChannel)):
            return await ctx.embed(
                "You can only hide text & voice channels!", 
                message_type="warned"
            )

        target = target or ctx.settings.lock_role

        if channel.overwrites_for(target).read_messages is True:
            return await ctx.embed(
                f"{channel.mention} is already revealed for {target.mention}!"
                if target != ctx.settings.lock_role
                else f"{channel.mention} is already revealed!",
                message_type="warned"
            )

        overwrite = channel.overwrites_for(target)
        overwrite.read_messages = True
        await channel.set_permissions(
            target,
            overwrite=overwrite,
            reason=f"{ctx.author.name} / {reason}",
        )

        return await ctx.embed(
            f"{channel.mention} is now revealed for {target.mention}"
            if target != ctx.settings.lock_role
            else f"{channel.mention} is now revealed",
            message_type="approved"
        )

    @hybrid_group(
        aliases=["slowmo", "slow"],
        invoke_without_command=True,
        example="#general 5m",
    )
    @has_permissions(manage_channels=True)
    async def slowmode(
        self,
        ctx: Context,
        channel: Optional[TextChannel],
        delay: timedelta = parameter(
            converter=Duration(
                min=timedelta(seconds=0),
                max=timedelta(hours=6),
            ),
        ),
    ) -> Message:
        """
        Set the slowmode for a channel.
        """
        channel = cast(TextChannel, channel or ctx.channel)
        if not isinstance(channel, TextChannel):
            return await ctx.embed("You can only set the slowmode for text channels!", message_type="warned")

        if channel.slowmode_delay == delay.seconds:
            return await ctx.embed(
                f"{channel.mention} already has a slowmode of **{precisedelta(delay)}**!",
                message_type="warned"
            )

        await channel.edit(slowmode_delay=delay.seconds)
        return await ctx.embed(
            f"Set the slowmode for {channel.mention} to **{precisedelta(delay)}**",
            message_type="approved"
        )

    @slowmode.command(
        name="disable",
        aliases=["off"],
        example="#general",
    )
    @has_permissions(manage_channels=True)
    async def slowmode_disable(
        self,
        ctx: Context,
        channel: Optional[TextChannel],
    ) -> Message:
        """
        Disable slowmode for a channel.
        """
        channel = cast(TextChannel, channel or ctx.channel)
        if not isinstance(channel, TextChannel):
            return await ctx.embed("You can only set the slowmode for text channels!", message_type="warned")

        if channel.slowmode_delay == 0:
            return await ctx.embed(f"{channel.mention} already has slowmode disabled!", message_type="warned")

        await channel.edit(slowmode_delay=0)
        return await ctx.embed(f"Disabled slowmode for {channel.mention}", message_type="approved")

    @hybrid_command(aliases=["naughty", "sfw"], example="#nsfw")
    @has_permissions(manage_channels=True)
    async def nsfw(
        self,
        ctx: Context,
        channel: Optional[TextChannel],
    ) -> Message:
        """
        Mark a channel as NSFW or SFW.
        """
        channel = cast(TextChannel, channel or ctx.channel)
        if not isinstance(channel, TextChannel):
            return await ctx.embed("You can only mark text channels as NSFW!", message_type="warned")

        await channel.edit(
            nsfw=not channel.is_nsfw(),
            reason=f"Changed by {ctx.author.name} ({ctx.author.id})",
        )
        return await ctx.embed(
            f"Marked {channel.mention} as **{'NSFW' if channel.is_nsfw() else 'SFW'}**",
            message_type="approved"
        )

    @hybrid_group(invoke_without_command=True)
    @has_permissions(manage_channels=True)
    async def topic(
        self,
        ctx: Context,
        channel: Optional[TextChannel],
        *,
        text: Range[str, 1, 1024],
    ) -> Message:
        """
        Set a channel's topic.
        """
        channel = cast(TextChannel, channel or ctx.channel)
        if not isinstance(channel, TextChannel):
            return await ctx.embed("You can only set the topic for text channels!", message_type="warned")

        try:
            await channel.edit(
                topic=text, reason=f"Changed by {ctx.author.name} ({ctx.author.id})"
            )
        except RateLimited as exc:
            retry_after = timedelta(seconds=exc.retry_after)
            return await ctx.embed(
                f"The channel is currently ratelimited, try again in **{precisedelta(retry_after)}**!", message_type="warned"
            )

        except HTTPException as exc:
            return await ctx.embed(
                f"Failed to set the topic for {channel.mention}!", codeblock(exc.text), message_type="warned"
            )

        return await ctx.embed(f"Set the topic for {channel.mention} to `{text}`", message_type="approved")

    @topic.command(
        name="remove",
        aliases=["delete", "del", "rm"],
    )
    @has_permissions(manage_channels=True)
    async def topic_remove(
        self,
        ctx: Context,
        channel: Optional[TextChannel],
    ) -> Message:
        """
        Remove a channel's topic.
        """

        channel = cast(TextChannel, channel or ctx.channel)
        if not isinstance(channel, TextChannel):
            return await ctx.embed("You can only remove the topic for text channels!", message_type="warned")

        if not channel.topic:
            return await ctx.embed(f"{channel.mention} doesn't have a topic!", message_type="warned")

        try:
            await channel.edit(
                topic="", reason=f"Changed by {ctx.author.name} ({ctx.author.id})"
            )
        except RateLimited as exc:
            retry_after = timedelta(seconds=exc.retry_after)
            return await ctx.embed(
                f"The channel is currently ratelimited, try again in **{precisedelta(retry_after)}**!", message_type="warned"
            )

        except HTTPException as exc:
            return await ctx.embed(
                f"Failed to remove the topic for {channel.mention}!",
                codeblock(exc.text),
                message_type="warned",
            )

        return await ctx.embed(f"Removed the topic for {channel.mention}", message_type="approved")

    @hybrid_group(invoke_without_command=True)
    @has_permissions(manage_channels=True)
    async def drag(
        self,
        ctx: Context,
        *members: Annotated[
            Member,
            TouchableMember,
        ],
        channel: Optional[VoiceChannel | StageChannel] = None,
    ) -> Message:
        """
        Drag member(s) to the voice channel.
        """
        if not channel:
            if not ctx.author.voice or not ctx.author.voice.channel:
                return await ctx.embed("You aren't in a voice channel!", message_type="warned")

            channel = ctx.author.voice.channel

        moved: int = 0
        for member in members:
            if member in channel.members:
                continue

            with suppress(HTTPException):
                await member.move_to(
                    channel,
                    reason=f"{ctx.author} dragged member",
                )

                moved += 1

        return await ctx.embed(
            f"Moved `{moved}`/`{len(members)}` member{'s' if moved != 1 else ''} to {channel.mention}",
            message_type="approved"
        )

    @drag.command(name="all", aliases=["everyone"])
    @has_permissions(manage_channels=True)
    @max_concurrency(1, BucketType.member)
    @cooldown(1, 10, BucketType.member)
    async def drag_all(
        self,
        ctx: Context,
        *,
        channel: VoiceChannel | StageChannel,
    ) -> Message:
        """
        Move all members to another voice channel.
        """

        if not ctx.author.voice or not ctx.author.voice.channel:
            return await ctx.embed("You aren't in a voice channel!", message_type="warned")

        elif ctx.author.voice.channel == channel:
            return await ctx.embed(f"You're already connected to {channel.mention}!", message_type="warned")

        members = ctx.author.voice.channel.members
        moved = 0
        for member in members:
            with suppress(HTTPException):
                await member.move_to(
                    channel,
                    reason=f"{ctx.author} moved all members",
                )

                moved += 1

        return await ctx.embed(
            f"Moved `{moved}`/`{len(members)}` member{'s' if moved != 1 else ''} to {channel.mention}",
            message_type="approved"
        )

    @hybrid_command(aliases=["mvall"])
    @has_permissions(manage_channels=True)
    async def moveall(
        self,
        ctx: Context,
        *,
        channel: VoiceChannel | StageChannel,
    ) -> Message:
        """
        Move all members to another voice channel.
        This is an alias for the `drag all` command.
        """
        return await ctx.invoke(self.drag_all, channel=channel)

    @hybrid_command(aliases=["newmembers"], example="15")
    async def newusers(
        self,
        ctx: Context,
        *,
        amount: Range[int, 5, 100] = 10,
    ) -> Message:
        """
        View a list of the newest members.

        This is useful to check for suspicious members.
        The amount parameter is limited to 100 results.
        """

        if not ctx.guild.chunked:
            await ctx.guild.chunk(cache=True)

        members = sorted(
            ctx.guild.members,
            key=lambda member: (member.joined_at or ctx.guild.created_at),
            reverse=True,
        )[:amount]

        return await ctx.paginate(entries=members, embed=Embed(title=f"{len(members)} Newest Members"))

    @command()
    @has_permissions(view_audit_log=True)
    async def audit(
        self,
        ctx: Context,
        user: Optional[Member | User],
        action: Optional[str],
    ) -> Message:
        """
        View server audit log entries.
        """
        _action = (action or "").lower().replace(" ", "_")
        if action and not self.actions.get(_action):
            return await ctx.embed(f"`{action}` isn't a valid action!", message_type="warned")

        entries: List[str] = []
        async for entry in ctx.guild.audit_logs(
            limit=100,
            user=user or MISSING,
            action=getattr(AuditLogAction, _action, MISSING),
        ):
            target: Optional[str] = None
            if entry.target:
                with suppress(TypeError):
                    if isinstance(entry.target, GuildChannel):
                        target = f"[#{entry.target}]({entry.target.jump_url})"
                    elif isinstance(entry.target, Role):
                        target = f"@{entry.target}"
                    elif isinstance(entry.target, Object):
                        target = f"`{entry.target.id}`"
                    else:
                        target = str(entry.target)

            entries.append(
                f"**{entry.user}** {self.actions.get(entry.action.name, entry.action.name.replace('_', ' '))} "
                + (f"**{target}**" if target and "`" not in target else target or "")
            )

        if not entries:
            return await ctx.embed(
                "No **audit log** entries found"
                + (f" for **{user}**" if user else "")
                + (f" with action **{action}**" if action else "")
                + "!",
                message_type="warned",
            )

        return await ctx.paginate(entries=entries, embed=Embed(title="Audit Log Entries"))

    @hybrid_command(aliases=["boot", "k"], example="@x 1d bot owner")
    @has_permissions(kick_members=True)
    @max_concurrency(1, BucketType.member)
    async def kick(
        self,
        ctx: Context,
        member: Annotated[
            Member,
            TouchableMember,
        ],
        *,
        reason: str = "No reason provided",
    ) -> Optional[Message]:
        """
        Kick a member from the server.
        """
        if await self.is_immune(ctx, member):
            return

        if member.premium_since:
            await ctx.prompt(
                f"Are you sure you want to **kick** {member.mention}?",
                "They are currently boosting the server!",
            )

        config = await Settings.fetch(self.bot, ctx.guild)
        if (
            config
            and config.kick
            and not config.is_whitelisted(ctx.author)
            and await config.check_threshold(self.bot, ctx.author, "kick")
        ):
            await strip_roles(
            ctx.author, dangerous=True, reason="Antinuke kick threshold reached"
            )
            return await ctx.embed(
            "You've exceeded the antinuke threshold for **kicks**!",
            "Your **administrative permissions** have been revoked",
            message_type="warned"
            )

        await member.kick(reason=f"{ctx.author} / {reason}")
        if ctx.settings.invoke_kick:
            script = Script(
            ctx.settings.invoke_kick,
            [
                ctx.guild,
                ctx.channel,
                member,
                (reason, "reason"),
                (ctx.author, "moderator"),
            ],
            )
            with suppress(HTTPException):
                await script.send(ctx)

        return await ctx.embed(
            f"Successfully kicked {member.mention}",
            message_type="approved"
        )

    @command(
        aliases=["hb"],
    )
    @has_permissions(ban_members=True)
    async def hardban(
        self,
        ctx: Context,
        user: Member | User,
        history: Optional[int] = 0,
        *,
        reason: str = "No reason provided",
    ) -> Optional[Message]:
        """
        Permanently ban a user from the server.

        Only the server owner is able to unban them.
        Re-running this command will remove the hard ban.
        """
        if history > 7:
            return await ctx.embed("You can only delete messages up to **7 days**!", message_type="warned")

        if isinstance(user, Member):
            await TouchableMember().check(ctx, user)

        if isinstance(user, Member) and await self.is_immune(ctx, user):
            return

        config = await Settings.fetch(self.bot, ctx.guild)
        if not config.is_trusted(ctx.author):
            return await ctx.embed(
                "You must be a **trusted administrator** to use this command!",
                message_type="warned"
            )

        hardban = await self.bot.pool.fetchrow(
            """
            SELECT * FROM 
            hardban WHERE 
            guild_id = $1 
            AND user_id = $2
            """,
            ctx.guild.id,
            user.id,
        )

        if hardban:
            await self.bot.pool.execute(
                """
                DELETE FROM hardban 
                WHERE guild_id = $1 
                AND user_id = $2
                """,
                ctx.guild.id,
                user.id,
            )
            with suppress(NotFound):
                await ctx.guild.unban(
                    user, reason=f"Hard ban removed by {ctx.author} ({ctx.author.id})"
                )

            try:
                await ModConfig.sendlogs(self.bot, "hardunban", ctx.author, user, reason)  # type: ignore
            except:
                pass
            return await ctx.embed(f"Hard ban removed for **{user}**", message_type="approved")

        await self.bot.pool.execute(
            """
            INSERT INTO hardban 
            (guild_id, user_id) 
            VALUES ($1, $2)
            """,
            ctx.guild.id,
            user.id,
        )
        await ModConfig.sendlogs(self.bot, "hardban", ctx.author, user, reason)  # type: ignore
        await ctx.guild.ban(
            user,
            delete_message_days=history, 
            reason=f"{ctx.author} / {reason}",
        )
        if ctx.settings.invoke_ban:
            script = Script(
                ctx.settings.invoke_ban,
                [
                    ctx.guild,
                    ctx.channel,
                    user,
                    (reason, "reason"),
                    (ctx.author, "moderator"),
                ],
            )
            with suppress(HTTPException):
                await script.send(ctx)

        return await ctx.embed("Hard ban applied successfully.", message_type="approved")

    @command(name="hardbanlist", aliases=["ls"])
    @has_permissions(ban_members=True)
    async def hardban_list(self, ctx: Context) -> Message:
        """
        View all hard banned users.
        """
        hardban = await self.bot.pool.fetch("SELECT user_id FROM hardban WHERE guild_id = $1", ctx.guild.id)

        config = await Settings.fetch(self.bot, ctx.guild)
        if not config.is_trusted(ctx.author):
            return await ctx.embed(
                "You must be a **trusted administrator** to use this command!",
                message_type="warned"
            )

        if not hardban:
            return await ctx.embed("No users are hard banned!", message_type="warned")
        
        entries = [
            f"**{self.bot.get_user(int(user_id['user_id'])) or 'Unknown User'}** (`{user_id['user_id']}`)"
            for user_id in hardban
        ]
        
        return await ctx.paginate(
            entries=entries,
            embed=Embed(title="Hard Banned Users")
        )

    @command(aliases=["massb"])
    @has_permissions(ban_members=True)
    async def massban(
        self,
        ctx: Context,
        users: Greedy[Member | User],
        history: Optional[Range[int, 0, 7]] = None,
        *,
        reason: str = "No reason provided",
    ) -> Optional[Message]:
        """
        Ban multiple users from the server.

        This command is limited to 150 users at a time.
        If you want to hard ban users, add `--hardban` to the reason.
        """
        for user in users:
            if isinstance(user, Member) and await self.is_immune(ctx, user):
                return

        config = await Settings.fetch(self.bot, ctx.guild)
        if not config.is_trusted(ctx.author):
            return await ctx.embed(
                "You must be a **trusted administrator** to use this command!",
                message_type="warned"
            )

        elif not users:
            return await ctx.embed(
                "You need to provide at least one user!",
                message_type="warned"
            )

        elif len(users) > 150:
            return await ctx.embed(
                "You can only ban up to **150 users** at a time!",
                message_type="warned"
            )

        elif len(users) > 5:
            await ctx.prompt(f"Are you sure you want to **ban** `{len(users)}` users?")

        if "--hardban" in reason:
            reason = reason.replace("--hardban", "").strip()
            key = self.hardban_key(ctx.guild)
            await self.bot.redis.sadd(key, *[str(user.id) for user in users])

        async with ctx.typing():
            for user in users:
                if isinstance(user, Member):
                    await TouchableMember().check(ctx, user)

                await ctx.guild.ban(
                    user,
                    delete_message_days=history or 0,
                    reason=f"{ctx.author} / {reason} (MASS BAN)",
                )

        # try:
        #     await ModConfig.sendlogs(self.bot, "massban", ctx.author, users, reason)  # type: ignore
        # except:
        #     pass

        return await ctx.embed(
            "Mass ban completed successfully.",
            message_type="approved"
        )
    
    @command(name="fn", hidden=True)
    @has_permissions(manage_nicknames=True)
    async def fn(
        self,
        ctx: Context,
        member: Annotated[
            Member,
            TouchableMember,
        ],
        *,
        nickname: Range[str, 1, 32],
    ) -> None:
        """
        Force a member's nickname.
        """
        if await self.is_immune(ctx, member):
            return
        
        await self.bot.pool.execute(
            """
            INSERT INTO forcenick (guild_id, user_id, nickname)
            VALUES ($1, $2, $3)
            ON CONFLICT (guild_id, user_id)
            DO UPDATE SET nickname = $3
            """,
            ctx.guild.id,
            member.id,
            nickname,
        )

        await member.edit(
            nick=nickname,
            reason=f"{ctx.author} ({ctx.author.id})",
        )
        return await ctx.embed(
            f"Forced nickname for {member.mention} to `{nickname}`",
            message_type="approved"
        )

    @hybrid_command(aliases=["deport", "b"])
    @has_permissions(ban_members=True)
    @max_concurrency(1, BucketType.member)
    async def ban(
        self,
        ctx: Context,
        user: Member | User,
        history: Optional[Range[int, 0, 7]] = None,
        *,
        reason: str = "No reason provided",
    ) -> Optional[Message]:
        """
        Ban a user from the server.
        """
        if isinstance(user, Member) and await self.is_immune(ctx, user):
            return

        if isinstance(user, Member):
            await TouchableMember().check(ctx, user)

            if user.premium_since:
                await ctx.prompt(
                    f"Are you sure you want to **ban** {user.mention}?",
                    "They are currently boosting the server!",
                )

        config = await Settings.fetch(self.bot, ctx.guild)
        if (
            config.ban
            and not config.is_whitelisted(ctx.author)
            and await config.check_threshold(self.bot, ctx.author, "ban")
        ):
            await strip_roles(
                ctx.author, dangerous=True, reason="Antinuke ban threshold reached"
            )
            return await ctx.embed(
                "You've exceeded the antinuke threshold for **bans**!",
                "Your **administrative permissions** have been revoked",
                message_type="warned",
            )

        await ctx.guild.ban(
            user,
            delete_message_seconds=history * 86400 if history is not None else 0,
            reason=f"{ctx.author} / {reason}",
        )

        if ctx.settings.invoke_ban is not None:
            script = Script(
                ctx.settings.invoke_ban,
                [
                    ctx.guild,
                    ctx.channel,
                    user,
                    (reason, "reason"),
                    (ctx.author, "moderator"),
                ],
            )
            with suppress(HTTPException):
                await script.send(ctx)
        # try:
        #     await ModConfig.sendlogs(self.bot, "ban", ctx.author, user, reason)  # type: ignore
        # except:
        #     pass

        return await ctx.embed(
            f"Successfully banned {user.mention}",
            message_type="approved",
        )

    @hybrid_command()
    @has_permissions(ban_members=True)
    @max_concurrency(1, BucketType.member)
    async def softban(
        self,
        ctx: Context,
        member: Annotated[
            Member,
            TouchableMember,
        ],
        history: Optional[Range[int, 1, 7]] = None,
        *,
        reason: str = "No reason provided",
    ) -> Optional[Message]:
        """
        Ban then unban a member from the server.

        This is used to cleanup messages from the member.
        """
        if await self.is_immune(ctx, member):
            return

        if member.premium_since:
            await ctx.prompt(
                f"Are you sure you want to **ban** {member.mention}?",
                "They are currently boosting the server!",
            )

        config = await Settings.fetch(self.bot, ctx.guild)
        if (
            config.ban
            and not config.is_whitelisted(ctx.author)
            and await config.check_threshold(self.bot, ctx.author, "ban")
        ):
            await strip_roles(
                ctx.author, dangerous=True, reason="Antinuke ban threshold reached"
            )
            return await ctx.embed(
                "You've exceeded the antinuke threshold for **bans**!",
                "Your **administrative permissions** have been revoked",
                message_type="warned",
            )

        # try:
        #     await ModConfig.sendlogs(self.bot, "ban", ctx.author, member, reason)  # type: ignore
        # except:
        #     pass

        await ctx.guild.ban(
            member,
            delete_message_days=history or 0,
            reason=f"{ctx.author} / {reason}",
        )
        await ctx.guild.unban(member)
        if ctx.settings.invoke_ban:
            script = Script(
                ctx.settings.invoke_ban,
                [
                    ctx.guild,
                    ctx.channel,
                    member,
                    (reason, "reason"),
                    (ctx.author, "moderator"),
                ],
            )
            with suppress(HTTPException):
                await script.send(ctx)

        return await ctx.embed(
            f"Successfully softbanned {member.mention}",
            message_type="approved",
        )

    @hybrid_group(
        aliases=["pardon", "unb"],
        invoke_without_command=True,
    )
    @has_permissions(ban_members=True)
    async def unban(
        self,
        ctx: Context,
        user: User,
        *,
        reason: str = "No reason provided",
    ):
        """
        Unban a user from the server.
        """
        hardban = await self.bot.pool.fetchrow(
            """
            SELECT * FROM 
            hardban WHERE 
            guild_id = $1 
            AND user_id = $2
            """,
            ctx.guild.id,
            user.id,
        )
        config = await Settings.fetch(self.bot, ctx.guild)
        if hardban and not config.is_trusted(ctx.author):
            return await ctx.embed(
                "You must be a **trusted administrator** to unban hard banned users!",
                message_type="warned"
            )

        try:
            await ctx.guild.unban(user, reason=f"{ctx.author} / {reason}")
        except NotFound:
            return await ctx.embed("That user is not banned!", message_type="warned")
        try:
            await ModConfig.sendlogs(self.bot, "unban", ctx.author, user, reason)  # type: ignore
        except:
            pass

        if ctx.settings.invoke_unban:
            script = Script(
                ctx.settings.invoke_unban,
                [
                    ctx.guild,
                    ctx.channel,
                    user,
                    (reason, "reason"),
                    (ctx.author, "moderator"),
                ],
            )
            with suppress(HTTPException):
                await script.send(ctx)

        return await ctx.embed(f"Successfully unbanned **{user.name}**", message_type="approved")

    @unban.command(name="all")
    @has_permissions(ban_members=True)
    @max_concurrency(1, BucketType.guild)
    async def unban_all(self, ctx: Context) -> Optional[Message]:
        """
        Unban all banned users from the server.
        """
        hardban_ids = await self.bot.pool.fetch(
            """
            SELECT user_id FROM 
            hardban WHERE 
            guild_id = $1
            """,
            ctx.guild.id,
        )

        hardban_ids = {record['user_id'] for record in hardban_ids}

        users = [
            entry.user
            async for entry in ctx.guild.bans()
            if entry.user.id not in hardban_ids
        ]
        if not users:
            return await ctx.embed("There are no banned users!", message_type="warned")

        await ctx.prompt(
            f"Are you sure you want to unban {plural(users, md='`'):user}?",
        )

        async with ctx.typing():
            for user in users:
                with suppress(HTTPException):
                    await ctx.guild.unban(
                        user, reason=f"{ctx.author} ({ctx.author.id}) / UNBAN ALL"
                    )

        return await ctx.embed("Successfully unbanned everyone", message_type="approved")

    @hybrid_group(
        aliases=["nick", "n"],
        invoke_without_command=True,
    )
    @has_permissions(manage_nicknames=True)
    async def nickname(
        self,
        ctx: Context,
        member: Annotated[
            Member,
            TouchableMember(
                allow_author=True,
            ),
        ],
        *,
        nickname: Range[str, 1, 32],
    ) -> Optional[Message]:
        """
        Change a member's nickname.
        """
        if await self.is_immune(ctx, member):
            return
        
        forcenick = await self.bot.pool.fetchval(
            """
            SELECT EXISTS(
                SELECT 1 FROM forcenick 
                WHERE guild_id = $1 
                AND user_id = $2
            )
            """,
            ctx.guild.id,
            member.id,
        )
        if forcenick:
            return await ctx.embed(
                f"{member.mention} has a forced nickname!\n",
                f"-# Use `{ctx.prefix}nickname remove {member}` to reset it",
                message_type="warned"
            )

        # try:
        #     await ModConfig.sendlogs(self.bot, "nickname", ctx.author, member, "No reason provided")  # type: ignore
        # except:
        #     pass

        await member.edit(
            nick=nickname,
            reason=f"{ctx.author} ({ctx.author.id})",
        )
        return await ctx.embed(
            f"Changed {member.mention}'s nickname to `{nickname}`",
            message_type="approved"
        )

    @nickname.command(
        name="remove",
        aliases=["reset", "rm"],
    )
    @has_permissions(manage_nicknames=True)
    async def nickname_remove(
        self,
        ctx: Context,
        member: Annotated[
            Member,
            TouchableMember,
        ],
    ) -> None:
        """
        Reset a member's nickname.
        """
        if await self.is_immune(ctx, member):
            return

        await self.bot.pool.execute(
            """
            DELETE FROM forcenick 
            WHERE guild_id = $1 
            AND user_id = $2
            """,
            ctx.guild.id,
            member.id,
        )

        await member.edit(
            nick=None,
            reason=f"{ctx.author} ({ctx.author.id})",
        )

        # try:
        #     await ModConfig.sendlogs(self.bot, "nickname remove", ctx.author, member, "None")  # type: ignore
        # except:
        #     pass

        return await ctx.embed(
            f"Reset {member.mention}'s nickname",
            message_type="approved"
        )

    @nickname.group(
        name="force",
        aliases=["lock"],
        invoke_without_command=True,
    )
    @has_permissions(manage_nicknames=True)
    async def nickname_force(
        self,
        ctx: Context,
        member: Annotated[
            Member,
            TouchableMember,
        ],
        *,
        nickname: Range[str, 1, 32],
    ) -> None:
        """
        Force a member's nickname.
        """
        if await self.is_immune(ctx, member):
            return
        
        await self.bot.pool.execute(
            """
            INSERT INTO forcenick (guild_id, user_id, nickname)
            VALUES ($1, $2, $3)
            ON CONFLICT (guild_id, user_id)
            DO UPDATE SET nickname = $3
            """,
            ctx.guild.id,
            member.id,
            nickname,
        )

        await member.edit(
            nick=nickname,
            reason=f"{ctx.author} ({ctx.author.id})",
        )
        
        # try:
        #     await ModConfig.sendlogs(self.bot, "forcenick", ctx.author, member, "No reason provided")  # type: ignore
        # except:
        #     pass
        
        return await ctx.embed(
            f"Forced nickname for {member.mention} to `{nickname}`",
            message_type="approved"
        )

    @nickname_force.command(
        name="cancel",
        aliases=["stop"],
    )
    @has_permissions(manage_nicknames=True)
    async def nickname_force_cancel(
        self,
        ctx: Context,
        member: Annotated[
            Member,
            TouchableMember,
        ],
    ) -> Optional[Message]:
        """
        Cancel a member's forced nickname.
        """
        await self.bot.pool.execute(
            """
            DELETE FROM forcenick 
            WHERE guild_id = $1 
            AND user_id = $2
            """,
            ctx.guild.id,
            member.id,
        )

        await member.edit(
            nick=None,
            reason=f"{ctx.author} ({ctx.author.id})",
        )
        
        # try:
        #     await ModConfig.sendlogs(self.bot, "forcenick remove", ctx.author, member, "No reason provided")  # type: ignore
        # except:
        #     pass
        
        return await ctx.embed(
            f"Cancelled forced nickname for {member.mention}",
            message_type="approved"
        )

    @hybrid_group(
        aliases=[
            "mute",
            "tmo",
            "to",
        ],
        invoke_without_command=True,
    )
    @has_permissions(moderate_members=True)
    async def timeout(
        self,
        ctx: Context,
        member: Annotated[
            Member,
            TouchableMember,
        ],
        duration: timedelta = parameter(
            converter=Duration(
                min=timedelta(seconds=60),
                max=timedelta(days=27),
            ),
            default=timedelta(minutes=5),
        ),
        *,
        reason: str = "No reason provided",
    ) -> Optional[Message]:
        """
        Timeout a member from the server.
        """
        if await self.is_immune(ctx, member):
            return

        await member.timeout(
            duration,
            reason=f"{ctx.author} / {reason}",
        )
        if ctx.settings.invoke_timeout:
            script = Script(
                ctx.settings.invoke_timeout,
                [
                    ctx.guild,
                    ctx.channel,
                    member,
                    (reason, "reason"),
                    (ctx.author, "moderator"),
                    (format_timespan(duration), "duration"),
                    (format_dt(utcnow() + duration, "R"), "expires"),
                    (str(int((utcnow() + duration).timestamp())), "expires_timestamp"),
                ],
            )
            with suppress(HTTPException):
                await script.send(ctx)

        # try:
        #     await ModConfig.sendlogs(
        #         self.bot, "timeout", ctx.author, member, reason
        #     )  # , duration=duratio
        # except:
        #     pass
        
        return await ctx.embed(
            f"Timed out {member.mention} for **{format_timespan(duration)}**",
            message_type="approved"
        )

    @timeout.command(
        name="list",
        aliases=["ls"],
    )
    @has_permissions(moderate_members=True)
    async def timeout_list(self, ctx: Context) -> Message:
        """
        View all timed out members.
        """

        members = list(
            filter(
                lambda member: member.is_timed_out(),
                ctx.guild.members,
            )
        )
        if not members:
            return await ctx.warn("No members are currently timed out!")

        entries=[
                f"{member.mention} - expires {format_dt(member.timed_out_until or utcnow(), 'R')}"
                for member in sorted(
                    members,
                    key=lambda member: member.timed_out_until or utcnow(),
                )
            ],

        return await ctx.paginate(entries=entries, embed=Embed(title="Timed Out Members"))
        
    @hybrid_group(
        aliases=[
            "unmute",
            "untmo",
            "unto",
            "utmo",
            "uto",
        ],
        invoke_without_command=True,
    )
    @has_permissions(moderate_members=True)
    async def untimeout(
        self,
        ctx: Context,
        member: Annotated[
            Member,
            TouchableMember,
        ],
        *,
        reason: str = "No reason provided",
    ) -> Optional[Message]:
        """
        Lift a member's timeout.
        """

        if not member.is_timed_out():
            return await ctx.embed("That member isn't timed out!", message_type="warned")

        await member.timeout(
            None,
            reason=f"{ctx.author} / {reason}",
        )
        if ctx.settings.invoke_untimeout:
            script = Script(
                ctx.settings.invoke_untimeout,
                [
                    ctx.guild,
                    ctx.channel,
                    member,
                    (reason, "reason"),
                    (ctx.author, "moderator"),
                ],
            )
            with suppress(HTTPException):
                await script.send(ctx)

        # try:
        #     await ModConfig.sendlogs(self.bot, "untimeout", ctx.author, member, reason)  # type: ignore
        # except:
        #     pass
        
        return await ctx.embed(
            f"Successfully lifted timeout for {member.mention}",
            message_type="approved"
        )

    @untimeout.command(name="all")
    @max_concurrency(1, BucketType.guild)
    @has_permissions(moderate_members=True)
    async def untimeout_all(self, ctx: Context) -> Optional[Message]:
        """
        Lift all timeouts.
        """

        members = list(
            filter(
                lambda member: member.is_timed_out(),
                ctx.guild.members,
            )
        )
        if not members:
            return await ctx.embed("No members are currently timed out!", message_type="warned")

        async with ctx.typing():
            for member in members:
                with suppress(HTTPException):
                    await member.timeout(
                        None,
                        reason=f"{ctx.author} ({ctx.author.id}) lifted all timeouts",
                    )
        
        return await ctx.embed("Successfully lifted all timeouts", message_type="approved")

    @group(
        aliases=["emote", "e", "jumbo"],
        invoke_without_command=True,
    )
    @has_permissions(manage_expressions=True)
    async def emoji(self, ctx: Context, emoji: PartialEmoji | str) -> Message:
        """
        Various emoji management commands.
        """

        if isinstance(emoji, str):
            url, name = unicode_emoji(emoji)
        else:
            url, name = emoji.url, emoji.name

        response = await self.bot.session.get(url)
        if not response.ok:
            return await ctx.embed("Failed to fetch the emoji!", message_type="warned")

        buffer = await response.read()
        _, suffix = url_to_mime(url)

        image, suffix = await enlarge_emoji(buffer, suffix[1:])
        if not image:
            return await ctx.embed("There was an issue downloading that emoji!", message_type="warned")

        try:
            return await ctx.embed(
                "Here is the enlarged emoji:",
                file=File(
                    BytesIO(image),
                    filename=f"{name}.{suffix}",
                ),
                message_type="approved"
            )
        except HTTPException:
            return await ctx.embed("The enlarged emoji was too large to send!", message_type="warned")

    @emoji.command(name="information", aliases=["i", "info", "details"])
    async def emoji_information(self, ctx: Context, emoji: PartialEmoji) -> Message:
        """
        View detailed information about an emoji.
        """
        button = Button(
            label="Emoji URL",
            style=discord.ButtonStyle.gray,
            emoji=emoji,
            url=f"{emoji.url}",
        )

        embed = Embed(
            title=f"{emoji.name}",
        )
        embed.set_thumbnail(url=emoji.url)
        embed.add_field(
            name="ID",
            value=emoji.id,
            inline=False,
        )
        embed.add_field(
            name="Animated",
            value=emoji.animated,
            inline=False,
        )
        embed.add_field(
            name="Code", 
            value=f"`{emoji}`", 
            inline=False
        )
        embed.add_field(
            name="Created At", 
            value=format_dt(emoji.created_at, "R"),
            inline=False,
        )
        
        view = View()
        view.add_item(button)
        
        return await ctx.send(embed=embed, view=view)

    @emoji.command(name="sticker")
    @has_permissions(manage_expressions=True)
    async def emoji_sticker(
        self, 
        ctx: Context, 
        name: Optional[Range[str, 2, 32]], 
        emoji: PartialEmoji
    ):
        """
        Convert a custom emoji to a sticker.
        """
        if len(ctx.guild.stickers) == ctx.guild.sticker_limit:
            return await ctx.embed(
                "The server is at the **maximum** amount of stickers!",
                message_type="warned"
            )
        
        try:
            sticker = await ctx.guild.create_sticker(
                name=name or emoji.name,
                description="ya",
                emoji=str(emoji),
                file=File(BytesIO(await emoji.read())),
                reason=f"Created by {ctx.author} ({ctx.author.id})",
            )
        except RateLimited as exc:
            retry_after = timedelta(seconds=exc.retry_after)
            return await ctx.embed(
                f"The server is currently ratelimited, try again in **{precisedelta(retry_after)}**!",
                message_type="warned"
            )

        except HTTPException as exc:
            return await ctx.embed(
                "Failed to create the sticker!", 
                codeblock(exc.text), 
                message_type="warned"
            )

        return await ctx.embed(
            f"Created sticker [{sticker.name}]({sticker.url})",
            message_type="approved"
        )

    @emoji.group(
        name="add",
        aliases=[
            "create",
            "upload",
            "steal",
        ],
        invoke_without_command=True,
    )
    @has_permissions(manage_expressions=True)
    async def emoji_add(
        self,
        ctx: Context,
        image: PartialEmoji | PartialAttachment = parameter(
            default=PartialAttachment.fallback,
        ),
        *,
        name: Optional[Range[str, 2, 32]],
    ) -> Optional[Message]:
        """
        Add an emoji to the server.
        """

        if not image.url:
            return await ctx.embed("Please provide a valid image or emoji!", message_type="warned")

        elif len(ctx.guild.emojis) == ctx.guild.emoji_limit:
            return await ctx.embed("The server is at the **maximum** amount of emojis!", message_type="warned")

        try:
            await ctx.guild.create_custom_emoji(
                name=name
                or (image.name if isinstance(image, PartialEmoji) else image.filename),
                image=(
                    await image.read()
                    if isinstance(image, PartialEmoji)
                    else image.buffer
                ),
                reason=f"Created by {ctx.author} ({ctx.author.id})",
            )
        except RateLimited as exc:
            retry_after = timedelta(seconds=exc.retry_after)
            return await ctx.embed(
                f"The server is currently ratelimited, try again in **{precisedelta(retry_after)}**!",
                message_type="warned"
            )

        except HTTPException as exc:
            return await ctx.embed("Failed to create the emoji!", codeblock(exc.text), message_type="warned")

        return await ctx.embed("Emoji added successfully", message_type="approved")

    @emoji_add.command(
        name="reactions",
        aliases=[
            "reaction",
            "reacts",
            "react",
        ],
    )
    @has_permissions(manage_expressions=True)
    async def emoji_add_reactions(
        self,
        ctx: Context,
        message: Optional[Message],
    ) -> Message:
        """
        Add emojis from the reactions on a message.
        """

        message = message or ctx.replied_message
        if not message:
            async for _message in ctx.channel.history(limit=25, before=ctx.message):
                if _message.reactions:
                    message = _message
                    break

        if not message:
            return await ctx.send_help(ctx.command)

        elif not message.reactions:
            return await ctx.embed("That message doesn't have any reactions!", message_type="warned")

        added_emojis: List[Emoji] = []
        async with ctx.typing():
            for reaction in message.reactions:
                if not reaction.is_custom_emoji():
                    continue

                emoji = reaction.emoji
                if isinstance(emoji, str):
                    continue

                try:
                    emoji = await ctx.guild.create_custom_emoji(
                        name=emoji.name,
                        image=await emoji.read(),
                        reason=f"Created by {ctx.author} ({ctx.author.id})",
                    )
                except RateLimited as exc:
                    return await ctx.embed(
                        f"Ratelimited after {plural(added_emojis, md='`'):emoji}!",
                        f"Please wait **{format_timespan(int(exc.retry_after))}** before trying again",
                        message_type="warned",
                    )

                except HTTPException:
                    if (
                        len(ctx.guild.emojis) + len(added_emojis)
                        > ctx.guild.emoji_limit
                    ):
                        return await ctx.embed(
                            "The maximum amount of emojis has been reached!",
                            message_type="warned",
                        )

                    break

                added_emojis.append(emoji)

        return await ctx.embed(
            f"Added {plural(added_emojis, md='`'):emoji} to the server"
            + (
                f" (`{len(message.reactions) - len(added_emojis)}` failed)"
                if len(added_emojis) < len(message.reactions)
                else ""
            ),
            message_type="approved",
        )

    @emoji_add.command(
        name="many",
        aliases=["bulk", "batch"],
    )
    @has_permissions(manage_expressions=True)
    async def emoji_add_many(
        self,
        ctx: Context,
        *emojis: PartialEmoji,
    ) -> Message:
        """
        Add multiple emojis to the server.
        """

        if not emojis:
            return await ctx.send_help(ctx.command)

        elif len(emojis) > 50:
            return await ctx.embed("You can only add up to **50 emojis** at a time!", message_type="warned")

        elif len(ctx.guild.emojis) + len(emojis) > ctx.guild.emoji_limit:
            return await ctx.embed(
                "The server doesn't have enough space for all the emojis!",
                message_type="warned",
            )

        added_emojis: List[Emoji] = []
        async with ctx.typing():
            for emoji in emojis:
                try:
                    emoji = await ctx.guild.create_custom_emoji(
                        name=emoji.name,
                        image=await emoji.read(),
                        reason=f"Created by {ctx.author} ({ctx.author.id})",
                    )
                except RateLimited as exc:
                    return await ctx.embed(
                        f"Ratelimited after {plural(added_emojis, md='`'):emoji}!",
                        f"Please wait **{format_timespan(int(exc.retry_after))}** before trying again",
                        message_type="warned",
                    )

                except HTTPException:
                    if len(ctx.guild.emojis) + len(emojis) > ctx.guild.emoji_limit:
                        return await ctx.embed(
                            "The maximum amount of emojis has been reached!",
                            message_type="warned",
                        )

                    break

                added_emojis.append(emoji)

        return await ctx.embed(
            f"Added {plural(added_emojis, md='`'):emoji} to the server"
            + (
                f" (`{len(emojis) - len(added_emojis)}` failed)"
                if len(added_emojis) < len(emojis)
                else ""
            ),
            message_type="approved",
        )

    @emoji.command(
        name="rename",
        aliases=["name"],
    )
    @has_permissions(manage_expressions=True)
    async def emoji_rename(
        self,
        ctx: Context,
        emoji: Emoji,
        *,
        name: str,
    ) -> Message:
        """
        Rename an existing emoji.
        """

        if emoji.guild_id != ctx.guild.id:
            return await ctx.embed("That emoji is not in this server!", message_type="warned")

        elif len(name) < 2:
            return await ctx.embed(
                "The emoji name must be at least **2 characters** long!",
                message_type="warned"
            )

        name = name[:32].replace(" ", "_")
        await emoji.edit(
            name=name,
            reason=f"Updated by {ctx.author} ({ctx.author.id})",
        )

        return await ctx.embed(f"Renamed the emoji to **{name}**", message_type="approved")

    @emoji.command(
        name="delete",
        aliases=["remove", "del"],
    )
    @has_permissions(manage_expressions=True)
    async def emoji_delete(
        self,
        ctx: Context,
        emoji: Emoji,
    ) -> Optional[Message]:
        """
        Delete an existing emoji.
        """

        if emoji.guild_id != ctx.guild.id:
            return await ctx.embed("That emoji is not in this server!", message_type="warned")

        await emoji.delete(reason=f"Deleted by {ctx.author} ({ctx.author.id})")
        return await ctx.embed(f"{emoji.name} deleted successfully", message_type="approved")

    @emoji.group(
        name="archive",
        aliases=["zip"],
        invoke_without_command=True,
    )
    @has_permissions(manage_expressions=True)
    @cooldown(1, 30, BucketType.guild)
    async def emoji_archive(self, ctx: Context) -> Message:
        """
        Archive all emojis into a zip file.
        """

        if ctx.guild.premium_tier < 2:
            return await ctx.embed(
                "The server must have at least Level 2 to use this command!",
                message_type="warned"
            )

        await ctx.embed(
            "Starting the archival process...",
            message_type="neutral"
        )

        async with ctx.typing():
            buffer = BytesIO()
            with ZipFile(buffer, "w") as zip:
                for index, emoji in enumerate(ctx.guild.emojis):
                    name = f"{emoji.name}.{emoji.animated and 'gif' or 'png'}"
                    if name in zip.namelist():
                        name = (
                            f"{emoji.name}_{index}.{emoji.animated and 'gif' or 'png'}"
                        )

                    __buffer = await emoji.read()

                    zip.writestr(name, __buffer)

            buffer.seek(0)

        if ctx.response:
            with suppress(HTTPException):
                await ctx.response.delete()

        return await ctx.embed(
            "Emoji archive created successfully.",
            file=File(
                buffer,
                filename=f"{ctx.guild.name}_emojis.zip",
            ),
            message_type="approved"
        )

    @emoji_archive.command(
        name="restore",
        aliases=["load"],
    )
    @has_permissions(manage_expressions=True)
    @max_concurrency(1, BucketType.guild)
    async def emoji_archive_restore(
        self,
        ctx: Context,
        attachment: PartialAttachment = parameter(
            default=PartialAttachment.fallback,
        ),
    ) -> Message:
        """
        Restore emojis from an archive.
        """

        if not attachment.is_archive():
            return await ctx.embed("The attachment must be a zip archive!", message_type="warned")

        await ctx.embed("Starting the restoration process...", message_type="neutral")

        emojis: List[Emoji] = []
        buffer = BytesIO(attachment.buffer)
        with ZipFile(buffer, "r") as zip:
            if len(zip.namelist()) > (ctx.guild.emoji_limit - len(ctx.guild.emojis)):
                return await ctx.embed(
                    "The server doesn't have enough space for all the emojis in the archive!",
                    message_type="warned",
                )

            for name in zip.namelist():
                if not name.endswith((".png", ".gif")):
                    continue

                name = name[:-4]
                if get(ctx.guild.emojis, name=name):
                    continue

                try:
                    emoji = await ctx.guild.create_custom_emoji(
                        name=name[:-4],
                        image=zip.read(name),
                        reason=f"Archive loaded by {ctx.author} ({ctx.author.id})",
                    )
                except RateLimited as exc:
                    return await ctx.embed(
                        f"Ratelimited after {plural(emojis, md='`'):emoji}!",
                        f"Please wait **{format_timespan(int(exc.retry_after))}** before trying again",
                        message_type="warned",
                    )

                except HTTPException:
                    if len(ctx.guild.emojis) == ctx.guild.emoji_limit:
                        return await ctx.embed(
                            "The maximum amount of emojis has been reached!",
                            message_type="warned",
                        )

                    break

                emojis.append(emoji)

        return await ctx.embed(
            f"Restored {plural(emojis, md='`'):emoji} from [`{attachment.filename}`]({attachment.url})",
            message_type="approved",
        )

    @group(name="sticker", invoke_without_command=True)
    @has_permissions(manage_expressions=True)
    async def sticker(self, ctx: Context) -> Message:
        """
        Various sticker related commands.
        """

        return await ctx.send_help(ctx.command)

    @sticker.command(
        name="add",
        aliases=["create", "upload"],
    )
    @has_permissions(manage_expressions=True)
    async def sticker_add(
        self,
        ctx: Context,
        name: Optional[Range[str, 2, 32]],
    ) -> Optional[Message]:
        """
        Add a sticker to the server.
        """

        if not ctx.message.stickers or not (sticker := ctx.message.stickers[0]):
            return await ctx.embed("Please provide a sticker to add!", message_type="warned")

        if len(ctx.guild.stickers) == ctx.guild.sticker_limit:
            return await ctx.embed(
                "The server is at the **maximum** amount of stickers!",
                message_type="warned"
            )

        sticker = await sticker.fetch()
        if not isinstance(sticker, GuildSticker):
            return await ctx.embed("Stickers cannot be default stickers!", message_type="warned")

        try:
            await ctx.guild.create_sticker(
                name=name or sticker.name,
                description=sticker.description,
                emoji=sticker.emoji,
                file=File(BytesIO(await sticker.read())),
                reason=f"Created by {ctx.author} ({ctx.author.id})",
            )

        except RateLimited as exc:
            retry_after = timedelta(seconds=exc.retry_after)
            return await ctx.embed(
                f"The server is currently ratelimited, try again in **{precisedelta(retry_after)}**!",
                message_type="warned"
            )

        except HTTPException as exc:
            return await ctx.embed(
                "Failed to create the sticker!",
                codeblock(exc.text),
                message_type="warned"
            )

        return await ctx.embed("Sticker added successfully", message_type="approved")

    @sticker.command(name="tag")
    @has_permissions(manage_expressions=True)
    async def sticker_tag(self, ctx: Context):
        """
        Rename all stickers to the server vanity.
        """
        if not ctx.guild.vanity_url_code:
            return await ctx.embed("The server doesn't have a vanity URL!", message_type="warned")
        
        async with ctx.typing():
            for sticker in ctx.guild.stickers:
                if ctx.guild.vanity_url_code in sticker.name:
                    continue
                try:
                    await sticker.edit(
                        name=f"{sticker.name} /{ctx.guild.vanity_url_code}",
                        reason=f"Updated by {ctx.author} ({ctx.author.id})",
                    )
                except HTTPException as e: 
                    return await ctx.embed(f"Failed to rename all stickers!\n{e}", message_type="warned")
            
            return await ctx.embed("Successfully renamed all stickers", message_type="approved")

    @sticker.command(
        name="steal",
        aliases=["grab"],
    )
    @has_permissions(manage_expressions=True)
    async def sticker_steal(
        self,
        ctx: Context,
        name: Optional[Range[str, 2, 32]] = None,
    ) -> Optional[Message]:
        """
        Steal a sticker from a message.
        """

        message: Optional[Message] = ctx.replied_message
        if not message:
            async for _message in ctx.channel.history(limit=25, before=ctx.message):
                if _message.stickers:
                    message = _message
                    break

        if not message:
            return await ctx.embed(
                "I couldn't find a message with a sticker in the past 25 messages!",
                message_type="warned"
            )

        if not message.stickers:
            return await ctx.embed(
                "That message doesn't have any stickers!",
                message_type="warned"
            )

        if len(ctx.guild.stickers) == ctx.guild.sticker_limit:
            return await ctx.embed(
                "The server is at the **maximum** amount of stickers!",
                message_type="warned"
            )

        sticker = await message.stickers[0].fetch()

        if not isinstance(sticker, GuildSticker):
            return await ctx.embed(
                "Stickers cannot be default stickers!",
                message_type="warned"
            )

        if sticker.guild_id == ctx.guild.id:
            return await ctx.embed(
                "That sticker is already in this server!",
                message_type="warned"
            )

        try:
            await ctx.guild.create_sticker(
                name=name or sticker.name,
                description=sticker.description,
                emoji=sticker.emoji,
                file=File(BytesIO(await sticker.read())),
                reason=f"Created by {ctx.author} ({ctx.author.id})",
            )
        except RateLimited as exc:
            retry_after = timedelta(seconds=exc.retry_after)
            return await ctx.embed(
                f"The server is currently ratelimited, try again in **{precisedelta(retry_after)}**!",
                message_type="warned"
            )

        except HTTPException as exc:
            return await ctx.embed(
                "Failed to create the sticker!",
                codeblock(exc.text),
                message_type="warned"
            )

        return await ctx.embed(
            "Sticker added successfully",
            message_type="approved"
        )

    @sticker.command(
        name="rename",
        aliases=["name"],
    )
    @has_permissions(manage_expressions=True)
    async def sticker_rename(
        self,
        ctx: Context,
        *,
        name: str,
    ) -> Message:
        """
        Rename an existing sticker.
        """

        sticker = None
        
        if ctx.message.stickers:
            sticker = ctx.message.stickers[0]
        
        elif ctx.replied_message and ctx.replied_message.stickers:
            sticker = ctx.replied_message.stickers[0]

        if not sticker:
            return await ctx.embed("Please provide a sticker to rename!", message_type="warned")

        sticker = await sticker.fetch()

        if not isinstance(sticker, GuildSticker):
            return await ctx.embed("Stickers cannot be default stickers!", message_type="warned")

        if sticker.guild_id != ctx.guild.id:
            return await ctx.embed("That sticker is not in this server!", message_type="warned")

        elif len(name) < 2:
            return await ctx.embed(
                "The sticker name must be at least **2 characters** long!",
                message_type="warned"
            )

        name = name[:32]
        await sticker.edit(
            name=name,
            reason=f"Updated by {ctx.author} ({ctx.author.id})",
        )

        return await ctx.embed(f"Renamed the sticker to **{name}**", message_type="approved")

    @sticker.command(
        name="delete",
        aliases=["remove", "del"],
    )
    @has_permissions(manage_expressions=True)
    async def sticker_delete(
        self,
        ctx: Context,
    ) -> Optional[Message]:
        """
        Delete an existing sticker.
        """

        if not (sticker := ctx.message.stickers[0]):
            return await ctx.embed("Please provide a sticker to delete!", message_type="warned")

        sticker = await sticker.fetch()

        if not isinstance(sticker, GuildSticker):
            return await ctx.embed("Stickers cannot be default stickers!", message_type="warned")

        if sticker.guild_id != ctx.guild.id:
            return await ctx.embed("That sticker is not in this server!", message_type="warned")

        await sticker.delete(reason=f"Deleted by {ctx.author} ({ctx.author.id})")
        return await ctx.embed("Sticker deleted successfully", message_type="approved")

    @sticker.command(
        name="archive",
        aliases=["zip"],
    )
    @has_permissions(manage_expressions=True)
    @cooldown(1, 30, BucketType.guild)
    async def sticker_archive(self, ctx: Context) -> Message:
        """
        Archive all stickers into a zip file.
        """

        if ctx.guild.premium_tier < 2:
            return await ctx.embed(
                "The server must have at least Level 2 to use this command!",
                message_type="warned"
            )

        message = await ctx.embed(
            "Starting the archival process...",
            message_type="neutral"
        )

        async with ctx.typing():
            buffer = BytesIO()
            with ZipFile(buffer, "w") as zip:
                for index, sticker in enumerate(ctx.guild.stickers):
                    name = f"{sticker.name}.{sticker.format}"
                    if name in zip.namelist():
                        name = f"{sticker.name}_{index}.{sticker.format}"

                    __buffer = await sticker.read()

                    zip.writestr(name, __buffer)

            buffer.seek(0)

        if ctx.response:
            with suppress(HTTPException):
                await ctx.response.delete()

        return await ctx.embed(
            "Sticker archive created successfully.",
            file=File(
                buffer,
                filename=f"{ctx.guild.name}_stickers.zip",
            ),
            message_type="approved",
            edit=message,
        )

    @group(
        name="set",
        aliases=["edit"],
        invoke_without_command=True,
    )
    @has_permissions(manage_guild=True)
    async def guild_set(self, ctx: Context) -> Message:
        """
        Various server related commands.
        """
        return await ctx.send_help(ctx.command)

    @guild_set.command(
        name="name",
        aliases=["n"]
    )
    @has_permissions(manage_guild=True)
    async def guild_set_name(
        self,
        ctx: Context,
        *,
        name: Range[str, 1, 100],
    ) -> Optional[Message]:
        """
        Change the server's name.
        """

        try:
            await ctx.guild.edit(
                name=name,
                reason=f"{ctx.author} ({ctx.author.id})",
            )
        except HTTPException:
            return await ctx.embed("Failed to change the server's name!", message_type="warned")

        return await ctx.embed("Server name changed successfully", message_type="approved")

    @guild_set.command(
        name="icon",
        aliases=[
            "pfp",
            "i",
        ],
    )
    @has_permissions(manage_guild=True)
    async def guild_set_icon(
        self,
        ctx: Context,
        attachment: PartialAttachment = parameter(
            default=PartialAttachment.fallback,
        ),
    ) -> Optional[Message]:
        """
        Change the server's icon.
        """

        if not attachment.is_image():
            return await ctx.embed("The attachment must be an image!", message_type="warned")

        await ctx.guild.edit(
            icon=attachment.buffer,
            reason=f"{ctx.author} ({ctx.author.id})",
        )
        return await ctx.embed("Server icon changed successfully", message_type="approved")

    @guild_set.command(
        name="splash",
        aliases=["background", "bg"],
    )
    @has_permissions(manage_guild=True)
    async def guild_set_splash(
        self,
        ctx: Context,
        attachment: PartialAttachment = parameter(
            default=PartialAttachment.fallback,
        ),
    ) -> Optional[Message]:
        """
        Change the server's splash.
        """

        if not attachment.is_image():
            return await ctx.embed("The attachment must be an image!", message_type="warned")

        await ctx.guild.edit(
            splash=attachment.buffer,
            reason=f"{ctx.author} ({ctx.author.id})",
        )
        return await ctx.embed("Server splash changed successfully", message_type="approved")

    @guild_set.command(
        name="banner",
        aliases=["b"],
    )
    @check(lambda ctx: bool(ctx.guild and ctx.guild.premium_tier >= 2))
    @has_permissions(manage_guild=True)
    async def guild_set_banner(
        self,
        ctx: Context,
        attachment: PartialAttachment = parameter(
            default=PartialAttachment.fallback,
        ),
    ) -> Optional[Message]:
        """
        Change the server's banner.
        """

        if not attachment.is_image():
            return await ctx.embed("The attachment must be an image!", message_type="warned")

        await ctx.guild.edit(
            banner=attachment.buffer,
            reason=f"{ctx.author} ({ctx.author.id})",
        )
        return await ctx.embed("Server banner changed successfully", message_type="approved")

    @guild_set.group(
        name="system",
        aliases=["sys"],
        invoke_without_command=True,
    )
    @has_permissions(manage_guild=True)
    async def guild_set_system(
        self,
        ctx: Context,
        *,
        channel: TextChannel,
    ) -> None:
        """
        Change the server's system channel.
        """

        await ctx.guild.edit(
            system_channel=channel,
            reason=f"{ctx.author} ({ctx.author.id})",
        )
        return await ctx.embed("System channel updated successfully", message_type="approved")

    @guild_set_system.group(
        name="welcome",
        aliases=["welc"],
        invoke_without_command=True,
    )
    @has_permissions(manage_guild=True)
    async def guild_set_system_welcome(self, ctx: Context) -> Message:
        """
        Toggle integrated welcome messages.
        """

        flags = ctx.guild.system_channel_flags
        flags.join_notifications = not flags.join_notifications

        await ctx.guild.edit(
            system_channel_flags=flags,
            reason=f"{ctx.author} ({ctx.author.id})",
        )
        return await ctx.embed(
            f"{'Now' if flags.join_notifications else 'No longer'} sending integrated **welcome messages**",
            message_type="approved"
        )

    @guild_set_system_welcome.command(
        name="sticker",
        aliases=["stickers", "wave"],
    )
    @has_permissions(manage_guild=True)
    async def guild_set_system_welcome_sticker(self, ctx: Context) -> Message:
        """
        Toggle replying with a welcome sticker.
        """

        flags = ctx.guild.system_channel_flags
        flags.join_notification_replies = not flags.join_notification_replies

        await ctx.guild.edit(
            system_channel_flags=flags,
            reason=f"{ctx.author} ({ctx.author.id})",
        )
        return await ctx.embed(
            f"{'Now' if flags.join_notification_replies else 'No longer'} adding a **welcome sticker**",
            message_type="approved"
        )

    @guild_set_system.command(
        name="boost",
        aliases=["boosts"],
    )
    @has_permissions(manage_guild=True)
    async def guild_set_system_boost(self, ctx: Context) -> Message:
        """
        Toggle integrated boost messages.
        """

        flags = ctx.guild.system_channel_flags
        flags.premium_subscriptions = not flags.premium_subscriptions

        await ctx.guild.edit(
            system_channel_flags=flags,
            reason=f"{ctx.author} ({ctx.author.id})",
        )
        return await ctx.embed(
            f"{'Now' if flags.premium_subscriptions else 'No longer'} sending integrated **boost messages**",
            message_type="approved"
        )

    @guild_set.command(
        name="notifications",
        aliases=["notis", "noti"],
    )
    @has_permissions(manage_guild=True)
    async def guild_set_notifications(
        self,
        ctx: Context,
        option: Literal["all", "mentions"],
    ) -> Message:
        """
        Change the server's default notification settings.
        """

        await ctx.guild.edit(
            default_notifications=(
                NotificationLevel.all_messages
                if option == "all"
                else NotificationLevel.only_mentions
            ),
            reason=f"{ctx.author} ({ctx.author.id})",
        )
        return await ctx.embed(
            "Server notification settings updated successfully.",
            message_type="approved"
        )

    @command()
    @has_permissions(manage_channels=True)
    async def nuke(self, ctx: Context) -> Message:
        """
        Clone the current channel.
        This action is irreversable and will delete the channel.
        """

        channel = ctx.channel
        if not isinstance(channel, TextChannel):
            return await ctx.warn("You can only nuke text channels!")

        await ctx.prompt(
            "Are you sure you want to **nuke** this channel?\n",
            "-# This action is **irreversable** and will delete the channel!",
        )

        new_channel = await channel.clone(
            reason=f"Nuked by {ctx.author} ({ctx.author.id})",
        )
        reconfigured = await self.reconfigure_settings(ctx.guild, channel, new_channel)
        await asyncio.gather(
            *[
                new_channel.edit(position=channel.position),
                channel.delete(reason=f"Nuked by {ctx.author} ({ctx.author.id})"),
            ]
        )

        embed = Embed(
            title="Channel Nuked",
            description=f"This channel has been nuked by {ctx.author.mention}",
        )
        if reconfigured:
            embed.add_field(
                name="**Reconfigured Settings**",
                value="" + "\n".join(reconfigured),
            )

        await new_channel.send(embed=embed)
        return await new_channel.send("first")

    @command()
    @has_permissions(manage_messages=True)
    async def pin(
        self,
        ctx: Context,
        message: Optional[Message],
    ) -> Optional[Message]:
        """
        Pin a specific message.
        """

        message = message or ctx.replied_message
        if not message:
            async for message in ctx.channel.history(limit=1, before=ctx.message):
                break

        if not message:
            return await ctx.send_help(ctx.command)

        elif message.guild != ctx.guild:
            return await ctx.embed("The message must be in this server!", message_type="warned")

        elif message.pinned:
            return await ctx.embed(
                f"That [`message`]({message.jump_url}) is already pinned!",
                message_type="warned"
            )

        await message.pin(reason=f"{ctx.author} ({ctx.author.id})")

    @command()
    @has_permissions(manage_messages=True)
    async def unpin(
        self,
        ctx: Context,
        message: Optional[Message],
    ) -> Optional[Message]:
        """
        Unpin a specific message.
        """

        message = message or ctx.replied_message
        if not message:
            return await ctx.send_help(ctx.command)

        elif message.guild != ctx.guild:
            return await ctx.embed("The message must be in this server!", message_type="warned")

        elif not message.pinned:
            return await ctx.embed(
                f"That [`message`]({message.jump_url}) is not pinned!",
                message_type="warned"
            )

        await message.unpin(reason=f"{ctx.author} ({ctx.author.id})")

    @hybrid_command()
    @has_permissions(administrator=True)
    async def strip(self, ctx: Context, user: Member, *, reason: str = "No reason provided"):
        """
        Strip a member of all dangerous permissions.
        """
        if isinstance(user, Member):
            await TouchableMember().check(ctx, user)

        if await self.is_immune(ctx, user):
            return

        roles_to_remove = []
        for role in user.roles[1:]:  
            for perm, value in role.permissions:
                if perm in DANGEROUS_PERMISSIONS and value:
                    roles_to_remove.append(role)
                    break

        if not roles_to_remove:
            return await ctx.embed(f"{user.mention} has no dangerous permissions to strip!", message_type="warned")

        key = self.restore_key(ctx.guild, user)
        role_ids = [r.id for r in roles_to_remove if r.is_assignable()]
        await self.bot.redis.set(key, role_ids, ex=86400)

        try:
            await user.remove_roles(*roles_to_remove, reason=f"Stripped by {ctx.author} ({ctx.author.id}): {reason}")
        except discord.HTTPException:
            return await ctx.embed("Failed to strip roles from the user!", message_type="warned")

        # try:
        #     await ModConfig.sendlogs(self.bot, "strip", ctx.author, user, reason)
        # except:
        #     pass

        return await ctx.embed(f"Stripped dangerous permissions from {user.mention}", message_type="approved")

    @has_permissions(guild_owner=True)
    @group(invoke_without_command=True, aliases=["fp"])
    async def fakepermissions(self, ctx: Context) -> Message:
        """
        Restrict moderators to only use Evict for moderation.
        """
        return await ctx.send_help(ctx.command)

    @has_permissions(guild_owner=True)
    @fakepermissions.command(
        name="grant",
        aliases=["add"],
    )
    async def fakepermissions_grant(
        self, ctx: Context, role: Role, *, permissions: str
    ):
        """
        Add one or more fake permissions to a role.
        > Can use multiple permissions at once if separated by a comma (,).
        > https://docs.evict.bot/configuration/fakepermissions
        """

        permissions_list = [perm.strip().lower() for perm in permissions.split(",")]

        # invalid_permissions = [perm for perm in permissions_list if perm not in map(str.lower, fake_permissions)]
        # if invalid_permissions:
        #     invalid_permissions_str = "\n".join(f"• `{perm}`" for perm in invalid_permissions)
        #     return await ctx.warn(f"Invalid permissions. Valid permissions are:\n{invalid_permissions_str}")

        invalid_permissions = [
            perm
            for perm in permissions_list
            if perm not in map(str.lower, fake_permissions)
        ]
        if invalid_permissions:
            # invalid_permissions_str = "\n".join(f"• `{perm}`" for perm in invalid_permissions)
            # valid_permissions_str = "\n".join(f"`{perm}`" for perm in fake_permissions)
            return await ctx.embed(
                f"Invalid permissions. Run ``{ctx.clean_prefix}fakepermissions permissions`` to view the list of valid permissions!",
                message_type="warned"
            )

        check = await self.bot.pool.fetchrow(
            f"""
            SELECT permission 
            FROM {FAKE_PERMISSIONS_TABLE} 
            WHERE guild_id = $1 AND role_id = $2
            """,
            ctx.guild.id,
            role.id,
        )

        if check:
            perms = json.loads(check[0])
            already_has = [perm for perm in permissions_list if perm in perms]
            if already_has:
                already_has_str = ", ".join(f"`{perm}`" for perm in already_has)
                return await ctx.embed(
                    f"{role.mention} already has the fake permissions: {already_has_str}!",
                    message_type="warned"
                )

            perms.extend(permissions_list)

            await self.bot.pool.execute(
                f"""
                UPDATE {FAKE_PERMISSIONS_TABLE} 
                SET permission = $1 
                WHERE guild_id = $2 
                AND role_id = $3
                """,
                json.dumps(perms),
                ctx.guild.id,
                role.id,
            )
        else:
            await self.bot.pool.execute(
                f"""
                INSERT INTO {FAKE_PERMISSIONS_TABLE} 
                (guild_id, role_id, permission) 
                VALUES ($1, $2, $3)
                """,
                ctx.guild.id,
                role.id,
                json.dumps(permissions_list),
            )

        added_permissions_str = ", ".join(f"`{perm}`" for perm in permissions_list)
        return await ctx.embed(
            f"Added {added_permissions_str} to the {role.mention}'s fake permissions",
            message_type="approved"
        )

    @has_permissions(guild_owner=True)
    @fakepermissions.command(
        name="revoke",
        aliases=["remove"],
    )
    async def fakepermissions_remove(
        self, ctx: Context, role: Role, *, permissions: str
    ):
        """
        Remove one or more fake permissions from a role's fake permissions.
        > Can use multiple permissions at once if separated by a comma (,).
        > https://docs.evict.bot/configuration/fakepermissions
        """

        permissions_list = [perm.strip().lower() for perm in permissions.split(",")]

        invalid_permissions = [
            perm
            for perm in permissions_list
            if perm not in map(str.lower, fake_permissions)
        ]
        if invalid_permissions:
            return await ctx.embed(
                f"Invalid permissions. Run `{ctx.clean_prefix}fakepermissions permissions` to view the list of valid permissions!",
                message_type="warned"
            )

        check = await self.bot.pool.fetchrow(
            f"""
            SELECT permission 
            FROM {FAKE_PERMISSIONS_TABLE} 
            WHERE guild_id = $1 
            AND role_id = $2""",
            ctx.guild.id,
            role.id,
        )

        if not check:
            return await ctx.embed(
                f"There are no fake permissions associated with {role.mention}!",
                message_type="warned"
            )

        perms = json.loads(check[0])

        removed_permissions = []
        for permission in permissions_list:
            if permission in perms:
                perms.remove(permission)
                removed_permissions.append(permission)

        if not removed_permissions:
            return await ctx.embed(
                f"{role.mention} does not have any of the specified fake permissions!",
                message_type="warned"
            )

        if perms:
            await self.bot.pool.execute(
                f"""
                UPDATE {FAKE_PERMISSIONS_TABLE} 
                SET permission = $1 
                WHERE guild_id = $2 
                AND role_id = $3""",
                json.dumps(perms),
                ctx.guild.id,
                role.id,
            )
        else:
            await self.bot.pool.execute(
                f"DELETE FROM {FAKE_PERMISSIONS_TABLE} WHERE guild_id = $1 AND role_id = $2",
                ctx.guild.id,
                role.id,
            )

        removed_permissions_str = ", ".join(f"`{perm}`" for perm in removed_permissions)
        return await ctx.embed(
            f"Removed {removed_permissions_str} from the {role.mention}'s fake permissions",
            message_type="approved"
        )

    @fakepermissions.command(
        name="list",
        aliases=["ls"],
    )
    @has_permissions(guild_owner=True)
    async def fakepermission_list(self, ctx: Context) -> Message:
        """
        View all fake permissions for the server.
        """
        records = await self.bot.pool.fetch(
            """
            SELECT role_id, permission
            FROM fake_permissions
            WHERE guild_id = $1
            """,
            ctx.guild.id,
        )

        fake_permissions = []
        for record in records:
            role = ctx.guild.get_role(record["role_id"])
            if role:
                permissions = json.loads(record["permission"])
                for perm in permissions:
                    fake_permissions.append(f"{role.mention} (`{perm}`)")

        if not fake_permissions:
            return await ctx.embed("No fake permissions exist for this server!", message_type="warned")

        return await ctx.paginate(entries=fake_permissions, embed=Embed(title="Fake Permissions"))

    @has_permissions(guild_owner=True)
    @fakepermissions.command(name="permissions", aliases=["perms"])
    async def fakepermissions_permissions(self, ctx: Context):
        """
        Get every valid permission that can be used for fake permissions.
        """
        embed = Embed(title="Valid Fake Permissions")
        embed.description = "\n".join(f"• `{perm}`" for perm in fake_permissions)

        return await ctx.paginate(entries=[embed], embed=embed)

    @command(example="@x")
    @has_permissions(manage_guild=True)
    async def modhistory(self, ctx: Context, moderator: Member = None):
        """
        View moderation history for a moderator.
        """
        moderator = moderator or ctx.author

        cases = await self.bot.pool.fetch(
            """
            SELECT * FROM history.moderation 
            WHERE moderator_id = $1 AND guild_id = $2 
            ORDER BY case_id DESC
            """,
            moderator.id,
            ctx.guild.id,
        )

        if not cases:
            return await ctx.embed(f"No moderation history found for {moderator.mention}!", message_type="warned")

        entries = [
            f"**Case #{case['case_id']}**\n"
            f"Action: {case['action']}\n"
            f"User: `{case['user_id']}`\n"
            f"Date: <t:{int(case['timestamp'].timestamp())}:f>\n"
            f"Reason: {case['reason']}"
            f"{f'\nDuration: {humanize.naturaldelta(case['duration'])}' if case['duration'] else ''}"
            for case in cases
        ]

        embed = Embed(title=f"Mod history for {moderator}")
        embed.set_footer(text=f"{len(cases)} total cases")

        return await ctx.paginate(entries=entries, embed=embed)

    @command(example="@x")
    @has_permissions(manage_guild=True)
    async def history(self, ctx: Context, user: Member | User = None):
        """
        View moderation history for a user.
        """
        user = user or ctx.author

        cases = await self.bot.pool.fetch(
            """
            SELECT * FROM history.moderation 
            WHERE user_id = $1 AND guild_id = $2 
            ORDER BY case_id DESC
            """,
            user.id,
            ctx.guild.id,
        )

        if not cases:
            return await ctx.embed(f"No moderation history found for {user.mention}!", message_type="warned")

        entries = [
            f"**Case #{case['case_id']}**\n"
            f"Action: {case['action']}\n"
            f"Moderator: `{case['moderator_id']}`\n"
            f"Date: <t:{int(case['timestamp'].timestamp())}:f>\n"
            f"Reason: {case['reason']}"
            f"{f'\nDuration: {humanize.naturaldelta(case['duration'])}' if case['duration'] else ''}"
            for case in cases
        ]

        embed = Embed(title=f"History for {user}")
        embed.set_footer(text=f"{len(cases)} total cases")

        return await ctx.paginate(entries=entries, embed=embed)

    @command(aliases=["pic", "pictureperms", "picture"])
    @has_permissions(manage_roles=True)
    async def picperms(
        self, ctx: Context, channel: Optional[TextChannel], user: Member
    ):
        """
        Toggle picture permissions for a user.
        """
        if channel is None:
            channel = ctx.channel

        if isinstance(user, Member):
            await TouchableMember().check(ctx, user)

        perms = channel.permissions_for(user)
        pic_perms = perms.attach_files and perms.embed_links

        if pic_perms:
            await channel.set_permissions(user, attach_files=False, embed_links=False)
            await ctx.embed(
                f"Revoked picture permissions from {user.mention} in {channel.mention}",
                message_type="approved"
            )
        else:
            await channel.set_permissions(user, attach_files=True, embed_links=True)
            await ctx.embed(
                f"Granted picture permissions to {user.mention} in {channel.mention}",
                message_type="approved"
            )

    # @group(name="warn", invoke_without_command=True, example="@x annoying")
    # @has_permissions(moderate_members=True)
    # @Mod.is_mod_configured()
    # async def warn(
    #     self,
    #     ctx: Context,
    #     member: Member,
    #     *,
    #     reason: str = "No reason provided"
    # ) -> Message:
    #     """Warn a member."""
        
    #     if isinstance(member, Member):
    #         await TouchableMember().check(ctx, member)

    #     if await self.is_immune(ctx, member):
    #         return
        
    #     warn_count = await self.bot.pool.fetchval(
    #         """
    #         SELECT COUNT(*) FROM history.moderation 
    #         WHERE guild_id = $1 AND user_id = $2 AND action = 'warn'
    #         """,
    #         ctx.guild.id, member.id
    #     )
        
    #     action = await self.bot.pool.fetchrow(
    #         """
    #         SELECT action, threshold, duration 
    #         FROM warn_actions 
    #         WHERE guild_id = $1 AND threshold = $2
    #         """,
    #         ctx.guild.id, warn_count + 1
    #     )

    #     await ModConfig.sendlogs(
    #         self.bot,
    #         "warn",
    #         ctx.author,
    #         member,
    #         reason
    #     )

    #     if not action:
    #         return await ctx.approve(f"Warned {member.mention}")

    #     duration = timedelta(seconds=action['duration']) if action['duration'] else None
        
    #     if action['action'] == 'timeout':
    #         await member.timeout(duration, reason="Warn threshold reached")
    #     elif action['action'] == 'jail':
    #         pass
    #     elif action['action'] == 'ban':
    #         await member.ban(reason="Warn threshold reached", delete_message_days=0)
    #     elif action['action'] == 'softban':
    #         await member.ban(reason="Warn threshold reached", delete_message_days=7)
    #         await member.unban(reason="Softban complete")
    #     elif action['action'] == 'kick':
    #         await member.kick(reason="Warn threshold reached")

    #     await ModConfig.sendlogs(
    #         self.bot,
    #         action['action'],
    #         ctx.guild.me,
    #         member,
    #         "Warn threshold reached",
    #         duration
    #     )

    #     return await ctx.approve(
    #         f"Warned {member.mention} (Threshold reached: {action['action']})"
    #     )

    # @warn.group(name="action", invoke_without_command=True)
    # @has_permissions(manage_guild=True)
    # async def warn_action(self, ctx: Context) -> Message:
    #     """Manage automated warn actions."""
    #     return await ctx.send_help(ctx.command)

    # @warn_action.command(name="add", example="ban --threshold 3")
    # @has_permissions(manage_guild=True)
    # async def warn_action_add(
    #     self,
    #     ctx: Context,
    #     action: str,
    #     *,
    #     flags: WarnActionFlags
    # ) -> Message:
    #     """Add an automated action for warn thresholds."""
        
    #     valid_actions = ["timeout", "jail", "ban", "softban", "kick"]
    #     action = action.lower()
        
    #     if action not in valid_actions:
    #         return await ctx.warn(
    #             f"Invalid action. Valid actions are: {', '.join(valid_actions)}"
    #         )
        
    #     await self.bot.pool.execute(
    #         """
    #         INSERT INTO warn_actions (guild_id, threshold, action, duration)
    #         VALUES ($1, $2, $3, $4)
    #         ON CONFLICT (guild_id, threshold) 
    #         DO UPDATE SET action = $3, duration = $4
    #         """,
    #         ctx.guild.id, flags.threshold, action, 
    #         int(flags.duration.total_seconds()) if flags.duration else None
    #     )

    #     return await ctx.approve(
    #         f"Set warn threshold {flags.threshold} to {action}" +
    #         (f" with duration {humanize.naturaldelta(flags.duration)}" if flags.duration else "")
    #     )

    # @warn_action.command(name="remove", example="3")
    # @has_permissions(manage_guild=True)
    # async def warn_action_remove(
    #     self,
    #     ctx: Context,
    #     threshold: int
    # ) -> Message:
    #     """Remove an automated action for a warn threshold."""
        
    #     deleted = await self.bot.pool.execute(
    #         """
    #         DELETE FROM warn_actions 
    #         WHERE guild_id = $1 AND threshold = $2
    #         """,
    #         ctx.guild.id, threshold
    #     )
        
    #     if deleted == "DELETE 0":
    #         return await ctx.warn(f"No action configured for threshold {threshold}")
        
    #     return await ctx.approve(f"Removed action for threshold {threshold}")

    # @warn_action.command(name="list")
    # @has_permissions(manage_guild=True)
    # async def warn_action_list(self, ctx: Context) -> Message:
    #     """List all configured warn actions."""
        
    #     actions = await self.bot.pool.fetch(
    #         """
    #         SELECT threshold, action, duration 
    #         FROM warn_actions 
    #         WHERE guild_id = $1 
    #         ORDER BY threshold
    #         """,
    #         ctx.guild.id
    #     )
        
    #     if not actions:
    #         return await ctx.warn("No warn actions configured")

    #     embed = Embed(title="Warn Actions")
        
    #     for action in actions:
    #         duration = timedelta(seconds=action['duration']) if action['duration'] else None
    #         embed.add_field(
    #             name=f"Threshold: {action['threshold']}",
    #             value=f"Action: {action['action']}\n" +
    #                   (f"Duration: {humanize.naturaldelta(duration)}" if duration else ""),
    #             inline=True
    #         )

    #     return await ctx.send(embed=embed)

    # @warn.command(name="remove", aliases=["delete", "del"], example="1 Resolved")
    # @has_permissions(moderate_members=True)
    # async def warn_remove(
    #     self,
    #     ctx: Context,
    #     case_id: Range[int, 1, None],
    #     *,
    #     reason: str = "No reason provided"
    # ) -> Message:
    #     """Remove a warning by case ID."""
        
    #     warn = await self.bot.pool.fetchrow(
    #         """
    #         DELETE FROM history.moderation 
    #         WHERE guild_id = $1 AND case_id = $2 AND action = 'warn'
    #         RETURNING user_id
    #         """,
    #         ctx.guild.id, case_id
    #     )
        
    #     if not warn:
    #         return await ctx.warn(f"No warning found with case ID #{case_id}")
            
    #     try:
    #         user = await self.bot.fetch_user(warn['user_id'])
    #         user_text = f"{user.mention} (`{user.id}`)"
    #     except:
    #         user_text = f"`{warn['user_id']}`"

    #     await ModConfig.sendlogs(
    #         self.bot,
    #         "warn remove",
    #         ctx.author,
    #         user,
    #         f"#{case_id} removed. {reason}"
    #     )

    #     return await ctx.approve(f"Removed warning case #{case_id} from {user_text}")      

    # @group(
    #     name="chunkban",
    #     aliases=["cb"],
    #     example="10",
    # )
    # @has_permissions(ban_members=True)
    # async def chunkban(
    #     self,
    #     ctx: Context,
    #     amount: Annotated[int, Range[int, 2, 100]] = 10,
    # ) -> Optional[Message]:
    #     """
    #     Ban a certain number of newest members from the server.
    #     """
    #     if await self.bot.redis.ratelimited(f"chunkban:{ctx.guild.id}", 1, 180):
    #         return await ctx.warn("This command can only be used **once per three minutes**!")

    #     if not ctx.guild.chunked:
    #         await ctx.guild.chunk(cache=True)

    #     config = await Settings.fetch(self.bot, ctx.guild)
    #     if not config.is_trusted(ctx.author):
    #         await ctx.warn(
    #             "You must be a **trusted administrator** to use this command!"
    #         )
    #         return False

    #     members = sorted(
    #         ctx.guild.members,
    #         key=lambda member: (member.joined_at or ctx.guild.created_at),
    #         reverse=True,
    #     )

    #     banned = members[:amount]

    #     if not banned:
    #         return await ctx.warn("No members found to ban!")

    #     await ctx.prompt(
    #         f"Are you sure you want to ban the newest {amount} members?",
    #     )

    #     banned_count = 0
    #     async with ctx.typing():
    #         for member in banned:
    #             if member.bot:
    #                 continue

    #             try:
    #                 await member.ban(reason=f"{ctx.author} / Chunkban")
    #                 await asyncio.sleep(2)
    #                 banned_count += 1
    #             except HTTPException:
    #                 continue

    #     return await ctx.approve(
    #         f"Banned {banned_count} out of {len(banned)} members."
    #     )

    # @chunkban.command(name="avatars", aliases=["defaultavatars"])
    # @has_permissions(ban_members=True)
    # async def chunkban_avatars(self, ctx: Context):
    #     """
    #     Ban members with default avatars.
    #     """
    #     if await self.bot.redis.ratelimited(f"chunkban:{ctx.guild.id}", 1, 180):
    #         return await ctx.warn("This command can only be used **once per three minutes**!")

    #     if not ctx.guild.chunked:
    #         await ctx.guild.chunk(cache=True)

    #     config = await Settings.fetch(self.bot, ctx.guild)
    #     if not config.is_trusted(ctx.author):
    #         await ctx.warn(
    #             "You must be a **trusted administrator** to use this command!"
    #         )
    #         return False

    #     members = [member for member in ctx.guild.members if member.default_avatar]

    #     if not members:
    #         return await ctx.warn("No members found with default avatars!")

    #     await ctx.prompt(
    #         f"Are you sure you want to ban members with default avatars?",
    #     )

    #     async with ctx.typing():
    #         for member in members:
    #             try:
    #                 await member.ban(reason=f"{ctx.author} / Chunkban: Default Avatar")
    #                 await asyncio.sleep(2)
    #             except HTTPException:
    #                 continue

    #     return await ctx.approve(
    #         f"Banned {plural(len(members), md='**')} members with default avatars."
    #     )
    
    # @group(name="immune", invoke_without_command=True)
    # async def immune(self, ctx: Context):
    #     """
    #     Make a user or role immune to moderation actions.
    #     """
    #     return await ctx.send_help(ctx.command)
    
    # @immune.group(name="add", invoke_without_command=True)
    # async def immune_add(self, ctx: Context):
    #     """
    #     Add user or role to immune list.
    #     """
    #     return await ctx.send_help(ctx.command)
    
    # @immune_add.command(name="user", aliases=["member"])
    # @has_permissions(manage_guild=True)
    # async def immune_add_user(self, ctx: Context, member: Member):
    #     """
    #     Add user to immune list.
    #     """
    #     immune = await self.bot.pool.fetchrow(
    #         """
    #         SELECT * FROM immune 
    #         WHERE guild_id = $1 
    #         AND entity_id = $2 
    #         AND type = 'user'
    #         """,
    #         ctx.guild.id, 
    #         member.id
    #     )

    #     if immune:
    #         return await ctx.warn(f"**{member.name}** is **already** immune!")
        
    #     await self.bot.pool.execute(
    #         """
    #         INSERT INTO immune 
    #         (guild_id, entity_id, type)
    #         VALUES 
    #         ($1, $2, 'user')
    #         """,
    #         ctx.guild.id, 
    #         member.id
    #     )
        
    #     return await ctx.approve(f"Added **{member.name}** to immune list!")
    
    # @immune_add.command(name="role")
    # @has_permissions(manage_guild=True)
    # async def immune_add_role(self, ctx: Context, role: Role):
    #     """
    #     Add role to immune list.
    #     """
    #     immune = await self.bot.pool.fetchrow(
    #         """
    #         SELECT * FROM immune 
    #         WHERE guild_id = $1 
    #         AND role_id = $2 
    #         AND type = 'role'
    #         """,
    #         ctx.guild.id, 
    #         role.id
    #     )

    #     if immune:
    #         return await ctx.warn(f"**{role.name}** is **already** immune!")

    #     await self.bot.pool.execute(
    #         """
    #         INSERT INTO immune 
    #         (guild_id, entity_id, role_id, type)
    #         VALUES 
    #         ($1, $2, $2, 'role')
    #         """,
    #         ctx.guild.id, 
    #         role.id
    #     )
        
    #     return await ctx.approve(f"Added {role.mention} to immune list!")

    # @immune.group(name="remove", invoke_without_command=True)
    # async def immune_remove(self, ctx: Context):
    #     """
    #     Remove user or role from immune list.
    #     """
    #     return await ctx.send_help(ctx.command)
    
    # @immune_remove.command(name="user", aliases=["member"])
    # @has_permissions(manage_guild=True)
    # async def immune_remove_user(self, ctx: Context, member: Member):
    #     """
    #     Remove user from immune list.
    #     """
    #     immune = await self.bot.pool.fetchrow(
    #         """
    #         SELECT * FROM immune 
    #         WHERE guild_id = $1 
    #         AND entity_id = $2 
    #         AND type = 'user'
    #         """,
    #         ctx.guild.id, 
    #         member.id
    #     )

    #     if not immune:
    #         return await ctx.warn(f"**{member.name}** is **not** immune!")

    #     await self.bot.pool.execute(
    #         """
    #         DELETE FROM immune 
    #         WHERE guild_id = $1 
    #         AND entity_id = $2 
    #         AND type = 'user'
    #         """,
    #         ctx.guild.id, 
    #         member.id
    #     )
        
    #     return await ctx.approve(f"Removed {member.mention} from immune list!")
    
    # @immune_remove.command(name="role")
    # @has_permissions(manage_guild=True)
    # async def immune_remove_role(self, ctx: Context, role: Role):
    #     """
    #     Remove role from immune list.
    #     """
    #     immune = await self.bot.pool.fetchrow(
    #         """
    #         SELECT * FROM immune 
    #         WHERE guild_id = $1 
    #         AND role_id = $2 
    #         AND type = 'role'
    #         """,
    #         ctx.guild.id, 
    #         role.id
    #     )

    #     if not immune:
    #         return await ctx.warn(f"**{role.name}** is **not** immune!")

    #     await self.bot.pool.execute(
    #         """
    #         DELETE FROM immune 
    #         WHERE guild_id = $1 
    #         AND role_id = $2 
    #         AND type = 'role'
    #         """,
    #         ctx.guild.id, 
    #         role.id
    #     )
        
    #     return await ctx.approve(f"Removed {role.mention} from immune list!")
    
    # @immune.command(name="list")
    # @has_permissions(manage_guild=True)
    # async def immune_list(self, ctx: Context):
    #     """
    #     List all immune users and roles.
    #     """
    #     immune = await self.bot.pool.fetch(
    #         """
    #         SELECT entity_id, role_id, type 
    #         FROM immune 
    #         WHERE guild_id = $1
    #         """,
    #         ctx.guild.id
    #     )
        
    #     if not immune:
    #         return await ctx.warn("No immune users or roles found!")
        
    #     entries = []

    #     for record in immune:
    #         entity_id = record['entity_id']
    #         role_id = record['role_id']
    #         type = record['type']
            
    #         if type == 'user':
    #             entries.append(f"<@{entity_id}>")
    #         elif type == 'role' and role_id is not None:
    #             entries.append(f"<@&{role_id}>")
        
    #     if not entries:
    #         return await ctx.warn("No immune users or roles found!")

    #     paginator = Paginator(
    #         ctx,
    #         entries=entries,
    #         embed=Embed(title="Immune Users and Roles")
    #     )
        
    #     return await paginator.start()


async def setup(bot: "Vesta") -> None:
    await bot.add_cog(Moderation(bot))
