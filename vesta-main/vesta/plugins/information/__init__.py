import time
import humanize

from datetime import datetime
from typing import Optional, List
from itertools import groupby
from yarl import URL
from urllib.parse import quote_plus

from discord import (
    User,
    Message,
    HTTPException,
    Embed,
    ButtonStyle,
    Member,
    Invite,
    TextChannel,
    Status,
    __version__,
    Role,
    ActivityType,
    Spotify,
    Streaming,
    Guild,
)
from discord.ext.commands import (
    Cog,
    command,
    CommandError,
    group,
    has_permissions,
    Author,
    parameter,
    hybrid_command,
)

from discord.app_commands import allowed_contexts, default_permissions, allowed_installs

from discord.ui import View, Button
from discord.utils import format_dt

from vesta.framework import Vesta, Context
from vesta.framework.tools.formatter import (
    human_join,
    shorten,
    short_timespan,
    codeblock,
    plural,
)
from vesta.framework.tools.converters import DANGEROUS_PERMISSIONS
from vesta.framework.script import Script

from .scrapers.cashapp import CashAppUser
from .scrapers.wiktionary import get_word_definition
from .scrapers.snap import Snapchat

# from .scrapers.google import GoogleMaps, GoogleMapsService
from .helpmenu import Help, HelpMenu


class Information(
    #  GoogleMaps,
    Help,
    Cog,
):
    def __init__(self, bot: Vesta):
        self.bot = bot
        #   self.maps = GoogleMapsService(bot)
        self.menu = HelpMenu(bot)

    @group(aliases=["nh", "names"], invoke_without_command=True)
    async def namehistory(self, ctx: Context, member: User = Author) -> Message:
        """
        View a member's name history.
        """
        record = await self.bot.pool.fetch(
            """
            SELECT *
            FROM name_history
            WHERE user_id = $1 
            """,
            member.id,
        )

        if not record:
            return await ctx.embed(f"**{member.name}** has no name history!", "warned")

        embed = Embed(title=f"Name history for {member.name}")

        names = [
            f"{entry['username']} - <t:{int(entry['changed_at'].timestamp())}:R>"
            for entry in record
        ]

        return await ctx.paginate(names, embed=embed)

    @namehistory.command(name="clear", aliases=["clean"])
    async def namehistory_clear(self, ctx: Context) -> Message:
        """
        Clear your name history.
        """
        record = await self.bot.pool.fetch(
            """
            SELECT *
            FROM name_history
            WHERE user_id = $1 
            """,
            ctx.author.id,
        )

        if not record:
            return await ctx.embed(f"You don't have a name history to clear!", "warned")

        await self.bot.pool.execute(
            """
            DELETE FROM name_history 
            WHERE user_id = $1
            """,
            ctx.author.id,
        )

        await ctx.prompt(
            "Are you sure you want to clear your name history?\n",
            "-# This action is **irreversable** and will delete the history.",
        )
        return await ctx.embed(f"Cleared all your name history", "approved")

    @command(aliases=["inv"])
    async def invite(self, ctx: Context) -> Message:
        """
        Invite Evict to your server.
        """
        embed = Embed(
            description=f"Invite **{self.bot.user.name.capitalize()}** to your server."
        )
        embed.set_author(
            name=ctx.author.display_name,
            icon_url=ctx.author.display_avatar.url,
        )

        view = View()
        view.add_item(
            Button(
                url=ctx.config.authentication.bot_invite,
                emoji=ctx.config.emojis.social.website,
                style=ButtonStyle.link,
            )
        )
        return await ctx.send(embed=embed, view=view)

    @command(aliases=["discord"])
    @has_permissions(guild_owner=True)
    async def support(self, ctx: Context) -> Message:
        """
        Join the support server.
        """
        embed = Embed(
            description=f"Join **{self.bot.user.name.capitalize()}** support server."
        )
        embed.set_author(
            name=ctx.author.display_name,
            icon_url=ctx.author.display_avatar.url,
        )

        view = View()
        view.add_item(
            Button(
                url=ctx.config.authentication.support_url,
                emoji=ctx.config.emojis.social.discord,
                style=ButtonStyle.link,
            )
        )
        return await ctx.send(embed=embed, view=view)

    @command(aliases=["av"])
    async def avatar(self, ctx: Context, member: User = None) -> Message:
        """
        View a member's avatar if available.
        """

        embed = Embed(
            url=member.avatar or member.default_avatar, title=f"{member.name}"
        )
        embed.set_author(
            name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url
        )
        embed.set_image(url=member.avatar or member.default_avatar)
        return await ctx.send(embed=embed)

    @command(aliases=["sav"])
    async def serveravatar(self, ctx: Context, member: Member = Author) -> Message:
        """
        View a member's server avatar if available.
        """
        if not member.guild_avatar:
            return await ctx.embed(
                f"**{member.name}** does not have a server avatar!"
                if member.id != ctx.author.id
                else "You don't have a server avatar!",
                "warned",
            )

        embed = Embed(url=member.guild_avatar, title=f"{member.name}")
        embed.set_author(
            name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url
        )
        embed.set_image(url=member.guild_avatar)
        return await ctx.send(embed=embed)

    @command(aliases=["mb", "mbanner"])
    async def memberbanner(self, ctx: Context, member: Member = Author) -> Message:
        """
        View a member's server banner if available.
        """
        if not member.guild_banner:
            return await ctx.embed(
                f"**{member.name}** does not have a server banner!"
                if member.id != ctx.author.id
                else "You don't have a server banner!",
                "warned",
            )

        embed = Embed(url=member.guild_banner, title=f"{member.name}")
        embed.set_author(
            name=ctx.author.display_name, icon_url=ctx.author.guild_banner.url
        )
        embed.set_image(url=member.guild_banner)
        return await ctx.send(embed=embed)

    @command(aliases=["sbanner"])
    async def serverbanner(self, ctx: Context, *, invite: Optional[Invite]) -> Message:
        """
        View a server's banner if available.
        """
        guild = invite.guild if invite else ctx.guild
        if not guild.banner:
            return await ctx.embed(
                f"**{guild.name}** does not have a banner!", "warned"
            )

        embed = Embed(url=guild.banner, title=f"{guild.name}'s banner")
        embed.set_author(
            name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url
        )
        embed.set_image(url=guild.banner)
        return await ctx.send(embed=embed)

    @command(aliases=["icon", "sicon"])
    async def servericon(self, ctx: Context, *, invite: Optional[Invite]) -> Message:
        """
        View a server's icon if available.
        """
        guild = invite.guild if invite else ctx.guild
        if not guild.icon:
            return await ctx.embed(f"**{guild.name}** does not have a icon!", "warned")

        embed = Embed(url=guild.icon, title=f"{guild.name}'s icon")
        embed.set_author(
            name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url
        )
        embed.set_image(url=guild.icon)
        return await ctx.send(embed=embed)

    @command()
    async def ping(self, ctx: Context) -> Message:
        """
        Check the bot's latency.
        """
        latency = round(self.bot.latency * 1000)
        start_time = time.time()
        message = await ctx.embed("ping...", "neutral")
        end_time = time.time()
        edit_latency = round((end_time - start_time) * 1000)
        return await ctx.embed(
            f"`{latency}ms` (edit: `{edit_latency}ms`)", "neutral", message
        )

    @command(aliases=["mc"])
    async def membercount(self, ctx: Context, *, invite: str = None) -> Message:
        """
        Shows the member statistics.
        """
        guild = ctx.guild
        fetched_invite = None

        if invite:
            try:
                code = invite.split("/")[-1].split(" ")[0]
                fetched_invite = await self.bot.fetch_invite(code)
                guild = fetched_invite.guild
            except:
                pass

        if fetched_invite and guild:
            total_members = fetched_invite.approximate_member_count or 0
            humans = None
            bots = None
            online = fetched_invite.approximate_presence_count or 0
            offline = idle = dnd = None
        else:
            total_members = guild.member_count
            humans = sum(not member.bot for member in guild.members)
            bots = total_members - humans
            online = sum(
                not member.bot and member.status == Status.online
                for member in guild.members
            )
            offline = sum(
                not member.bot and member.status == Status.offline
                for member in guild.members
            )
            idle = sum(
                not member.bot and member.status == Status.idle
                for member in guild.members
            )
            dnd = sum(
                not member.bot and member.status == Status.dnd
                for member in guild.members
            )

        embed = Embed()
        embed.set_author(
            name=guild.name, icon_url=guild.icon.url if guild.icon else None
        )
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
        embed.set_footer(text=f"Server ID: {guild.id}")

        humans_display = (
            f"**Humans:** {humans:,}" if humans is not None else "**Humans:** N/A"
        )
        bots_display = f"**Bots:** {bots:,}" if bots is not None else "**Bots:** N/A"

        embed.add_field(
            name="Member Count",
            value=f">>> **Total:** {total_members:,}\n{humans_display}\n{bots_display}",
            inline=False,
        )

        if fetched_invite:
            embed.add_field(
                name="Member Statuses",
                value=f">>> **Online:** {online:,}\n**Offline:** {total_members - online:,}",
                inline=False,
            )
        else:
            embed.add_field(
                name="Member Statuses",
                value=f">>> **Online:** {online:,}\n**Offline:** {offline:,}\n**Idle:** {idle:,}\n**DND:** {dnd:,}",
                inline=False,
            )

        return await ctx.send(embed=embed)

    @hybrid_command()
    @allowed_installs(guilds=True, users=True)
    @allowed_contexts(guilds=True, dms=True, private_channels=True)
    @default_permissions(use_application_commands=True)
    async def firstmessage(
        self, ctx: Context, channel: Optional[TextChannel] = None
    ) -> Message:
        """
        View the first message in a channel, or the specified channel.
        """
        if ctx.guild is None and channel is not None:
            return await ctx.embed("You cannot specify a channel in DMs!", "warned")

        channel = channel or ctx.channel
        messages = [
            message async for message in channel.history(limit=1, oldest_first=True)
        ]

        if not messages:
            return await ctx.embed(
                f"{channel.mention} does not have any messages!", "warned"
            )

        message = messages[0]
        return await ctx.embed(
            f"Jump to the [first message]({message.jump_url}) sent by **{message.author}**",
            "neutral",
        )

    @group(aliases=["servernames", "gnames", "snames"], invoke_without_command=True)
    async def guildnames(self, ctx: Context, guild: Optional[Guild] = None):
        """
        View a server's name history.
        """
        guild = guild or ctx.guild
        record = await self.bot.pool.fetch(
            """
            SELECT name, changed_at 
            FROM gnames 
            WHERE guild_id = $1 
            ORDER BY changed_at DESC
            """,
            guild.id,
        )

        if not record:
            return await ctx.embed(f"**{guild.name}** has no name history!", "warned")

        server_names = [
            f"{entry['name']} - <t:{int(entry['changed_at'].timestamp())}:R>"
            for entry in record
        ]

        embed = Embed(title=f"Name History for **{guild.name}**")

        return await ctx.paginate(server_names, embed=embed)

    @guildnames.command(name="clear")
    @has_permissions(manage_guild=True)
    async def clear_guildnames(self, ctx: Context) -> Message:
        """
        Clear a server's name history.
        """
        records = await self.bot.pool.execute(
            """
            DELETE FROM gnames 
            WHERE guild_id = $1
            """,
            ctx.guild.id,
        )
        if not records:
            return await ctx.embed(
                f"{ctx.guild.name} has no name history to clear!", "warned"
            )

        await ctx.prompt(
            "Are you sure you want to clear the guild name history?\n",
            "-# This action is **irreversable** and will delete the history.",
        )
        return await ctx.embed(
            f"Cleared all name history for **{ctx.guild.name}**", "approved"
        )

    @command()
    async def status(self, ctx: Context) -> Message:
        """
        Check shard status.
        """
        return await ctx.send(
            f"Check **bot** status [here](https://evict.bot/status).\n-# You are on shard `{ctx.guild.shard_id}`"
        )

    @command()
    async def shards(self, ctx: Context) -> Message:
        """
        Check information across all shards.
        """
        embed = Embed(description="Shard Information")
        embed.set_author(
            name=ctx.author.display_name,
            icon_url=ctx.author.display_avatar.url,
        )
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)

        for shard_id, shard in self.bot.shards.items():
            guilds = len([g for g in self.bot.guilds if g.shard_id == shard_id])
            users = sum(
                [g.member_count for g in self.bot.guilds if g.shard_id == shard_id]
            )
            embed.add_field(
                name=f"Shard {shard_id}",
                value=f">>> Guilds: `{guilds:,}`\nUsers: `{users:,}`\nLatency: `{round(shard.latency * 1000)}ms`",
                inline=True,
            )
        embed.set_footer(
            text=f"You are on shard {ctx.guild.shard_id} • {len(self.bot.guilds):,} guilds"
        )
        return await ctx.send(embed=embed)

    @command(aliases=["si", "sinfo"])
    async def serverinfo(self, ctx: Context, *, invite: str = None) -> Message:
        """
        View information regarding the server.
        """
        guild = ctx.guild
        fetched_invite = None

        if invite:
            try:
                code = invite.split("/")[-1].split(" ")[0]
                fetched_invite = await self.bot.fetch_invite(code)
                guild = fetched_invite.guild
            except:
                pass

        if not guild:
            return await ctx.embed("Invalid invite or server unavailable!", "warned")

        embed = Embed()

        if fetched_invite and guild:
            icon_url = guild.icon.url if guild.icon else None
            embed.set_author(name=f"{guild.name}", icon_url=icon_url)
            embed.set_thumbnail(url=icon_url)
            embed.set_footer(text=f"Server ID: {guild.id}")

            embed.description = f"**Created:** {format_dt(guild.created_at, style='D')} ({format_dt(guild.created_at, style='R')})"
            if guild.description:
                embed.description += f"\n-# {guild.description}"

            embed.add_field(
                name="Invite Information",
                value=(
                    f">>> **Code:** [{fetched_invite.code}](https://discord.gg/{fetched_invite.code})\n"
                    f"**Channel:** {fetched_invite.channel.name if fetched_invite.channel else 'Unknown'}\n"
                    f"**Expires:** {format_dt(fetched_invite.expires_at, style='R') if fetched_invite.expires_at else 'Never'}"
                ),
                inline=True,
            )
            embed.add_field(
                name="Server Information",
                value=(
                    f">>> **Members:** {fetched_invite.approximate_member_count:,}\n"
                    f"**Boosts:** {guild.premium_subscription_count}\n"
                    f"**Online:** {fetched_invite.approximate_presence_count:,}"
                ),
                inline=True,
            )

        else:
            icon_url = guild.icon.url if guild.icon else None
            banner_url = guild.banner.url if guild.banner else None
            description = guild.description or ""

            embed.description = (
                f"{description}\n**Created:** {format_dt(guild.created_at, style='F')} "
                f"({format_dt(guild.created_at, style='R')})"
            )
            embed.set_author(name=guild.name, icon_url=icon_url)
            embed.set_thumbnail(url=icon_url)
            embed.set_image(url=banner_url)

            embed.add_field(
                name="Counts",
                value=(
                    f">>> **Emojis:** {len(guild.emojis):,}\n"
                    f"**Roles:** {len(guild.roles):,}\n"
                    f"**Stickers:** {len(guild.stickers)}"
                ),
                inline=True,
            )

            embed.add_field(
                name="Members",
                value=(
                    f">>> **Humans:** {sum(1 for m in guild.members if not m.bot):,}\n"
                    f"**Bots:** {sum(1 for m in guild.members if m.bot):,}\n"
                    f"**Total:** {guild.member_count:,}"
                ),
                inline=True,
            )

            embed.add_field(
                name="Channels",
                value=(
                    f">>> **Text:** {len(guild.text_channels):,}\n"
                    f"**Voice:** {len(guild.voice_channels):,}\n"
                    f"**Categories:** {len(guild.categories):,}"
                ),
                inline=True,
            )

            embed.add_field(
                name="Boost",
                value=(
                    f">>> **Boosts:** {guild.premium_subscription_count:,}\n"
                    f"**Boosters:** {len(guild.premium_subscribers)}\n"
                    f"**Level:** {guild.premium_tier}"
                ),
                inline=True,
            )

            embed.add_field(
                name="Basic Info",
                value=(
                    f">>> **Owner:** {guild.owner} (`{guild.owner_id}`)\n"
                    f"**Verification:** {str(guild.verification_level).capitalize()}\n"
                    f"**Vanity URL:** {guild.vanity_url_code or 'None'}"
                ),
                inline=True,
            )

            embed.set_image(url=banner_url)
            embed.set_footer(text=f"Server ID: {guild.id}")

        return await ctx.send(embed=embed)

    @command(aliases=["bi", "binfo"])
    async def botinfo(self, ctx: Context) -> Message:
        """
        View information regarding the bot.
        """
        embed = Embed(
            description=f"Developed & maintained by the [Evict Team]({ctx.config.authentication.support_url})."
        )
        embed.set_author(
            name=f"{ctx.author.display_name}", icon_url=ctx.author.display_avatar.url
        )
        commands = len([cmd for cmd in self.bot.walk_commands() 
                        if cmd.cog_name not in ('Jishaku', 'Owner')])

        embed.add_field(
            name="Statistics",
            value=(
            f">>> **Users:** `{len(self.bot.users):,}`\n"
            f"**Commands:** `{commands}`\n"
            f"**Servers:** `{len(self.bot.guilds):,}`"
            ),
            inline=True,
        )

        embed.add_field(
            name="Bot",
            value=(
                f">>> **Latency:** `{round(self.bot.latency * 1000)}ms`\n"
                f"**Discord.py:** `{__version__}\n`"
                f"**Created:** <t:{int(self.bot.user.created_at.timestamp())}:R>"
            ),
            inline=True,
        )
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        embed.set_footer(
            text=f"Evict v{self.bot.version}", icon_url=self.bot.user.display_avatar.url
        )

        view = View()
        view.add_item(
            Button(
                label="Support",
                style=ButtonStyle.link,
                url="https://discord.com/invite/evict",
                emoji=ctx.config.emojis.social.discord,
            )
        )

        view.add_item(
            Button(
                label="Website",
                url="https://evict.bot/",
                style=ButtonStyle.link,
                emoji=ctx.config.emojis.social.website,
            )
        )
        return await ctx.send(embed=embed, view=view)

    @command(aliases=["ri"])
    async def roleinfo(self, ctx: Context, role: Optional[Role]) -> Message:
        """
        View information about a role.
        """
        if role is None:
            role = ctx.author.top_role or None
        embed = Embed(title=f"{role.name}", color=role.color)

        embed.set_author(
            name=f"{ctx.author.display_name}",
            icon_url=f"{ctx.author.display_avatar.url}",
        )
        embed.add_field(name="Role ID", value=f"``{role.id}``", inline=False)
        embed.add_field(name="Color", value=f"``{role.color}``", inline=False)

        granted_permissions = [
            perm for perm in DANGEROUS_PERMISSIONS if getattr(role.permissions, perm)
        ]

        if granted_permissions:
            embed.add_field(
                name="Permissions",
                value=(
                    ", ".join(granted_permissions)
                    if len(granted_permissions) > 1
                    else granted_permissions[0]
                ),
                inline=False,
            )

        else:
            embed.add_field(
                name="Permissions",
                value="No dangerous permissions granted.",
                inline=False,
            )

        members_with_role = role.members
        member_names = [member.name for member in members_with_role][:5]

        if member_names:
            embed.add_field(
                name=f"{len(role.members)} Member(s)",
                value=(
                    ", ".join(member_names)
                    if len(member_names) > 1
                    else member_names[0]
                ),
                inline=False,
            )

        else:
            embed.add_field(
                name="Members with this Role",
                value="No members in this role.",
                inline=False,
            )

        if role.icon:
            embed.set_thumbnail(url=role.icon.url)

        if granted_permissions:
            embed.set_footer(
                text="Dangerous Permissions!",
            )

        return await ctx.send(embed=embed)

    @command(aliases=["gbi"])
    async def getbotinvite(self, ctx: Context, *, user: User):
        """
        Get a bot's invite link with their ID.
        """
        if not user.bot:
            return await ctx.embed(f"**{user.name}** is not a bot!", "warned")

        view = View()
        view.add_item(
            Button(
                style=ButtonStyle.link,
                label=f"Invite {user.name}",
                url=f"https://discord.com/api/oauth2/authorize?client_id={user.id}&permissions=8&scope=bot%20applications.commands",
            )
        )

        return await ctx.send(view=view)

    @command()
    async def devices(self, ctx: Context, *, member: Member = Author) -> Message:
        """
        View a member's platforms.
        """
        if member.status == Status.offline:
            return await ctx.embed(
                (
                    f"You're offline!"
                    if member == ctx.author
                    else f"**{member.name}** is offline!"
                ),
                "warned",
            )

        device_emojis = {
            "Mobile": {
                Status.dnd: ctx.config.emojis.device.phone_dnd,
                Status.idle: ctx.config.emojis.device.phone_idle,
                Status.online: ctx.config.emojis.device.phone_online,
            },
            "Desktop": {
                Status.dnd: ctx.config.emojis.device.desk_dnd,
                Status.idle: ctx.config.emojis.device.desk_idle,
                Status.online: ctx.config.emojis.device.desk_online,
            },
            "Browser": {
                Status.dnd: ctx.config.emojis.device.web_dnd,
                Status.idle: ctx.config.emojis.device.web_idle,
                Status.online: ctx.config.emojis.device.web_online,
            },
        }

        embed = Embed()
        embed.set_author(
            name="Your devices" if member == ctx.author else f"{member.name}'s devices",
            icon_url=member.display_avatar.url,
        )

        embed.description = ""
        for activity_type, activities in groupby(
            member.activities,
            key=lambda activity: activity.type,
        ):
            activities = list(activities)
            if isinstance(activities[0], Spotify):
                activity = activities[0]
                embed.description += f"\n🎵 Listening to [**{activity.title}**]({activity.track_url}) by **{activity.artists[0]}**"  # type: ignore

            elif isinstance(activities[0], Streaming):
                embed.description += "\n🎥 Streaming " + human_join(
                    [
                        f"[**{activity.name}**]({activity.url})"
                        for activity in activities
                        if isinstance(activity, Streaming)
                    ],
                    final="and",
                )  # type: ignore

            elif activity_type == ActivityType.playing:
                embed.description += "\n🎮 Playing " + human_join(
                    [f"**{activity.name}**" for activity in activities],
                    final="and",
                )

            elif activity_type == ActivityType.watching:
                embed.description += "\n📺 Watching " + human_join(
                    [f"**{activity.name}**" for activity in activities],
                    final="and",
                )

            elif activity_type == ActivityType.competing:
                embed.description += "\n🏆 Competing in " + human_join(
                    [f"**{activity.name}**" for activity in activities],
                    final="and",
                )

        embed.description += "\n" + "\n".join(
            [
                f"{device_emojis[device].get(status, ctx.config.emojis.device.offline)} - **{device}**"
                for device, status in {
                    "Mobile": member.mobile_status,
                    "Desktop": member.desktop_status,
                    "Browser": member.web_status,
                }.items()
                if status != Status.offline
            ]
        )
        return await ctx.send(embed=embed)

    @command()
    async def roles(self, ctx: Context) -> Message:
        """
        View the server roles.
        """
        roles_reversed = reversed(ctx.guild.roles[1:])
        roles = [f"{role.mention} (`{role.id}`)" for role in roles_reversed]
        if not roles:
            return await ctx.embed("This server doesn't have any roles yet!", "warned")

        embed = Embed(title=f"{len(roles)} roles in {ctx.guild.name}")
        embed.set_author(
            name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url
        )

        return await ctx.paginate(roles, embed=embed)

    @command(aliases=["members"])
    async def inrole(self, ctx: Context, *, role: Optional[Role] = None) -> Message:
        """
        View members which have a role.
        """
        if role is None:
            role = next(
                (r for r in reversed(ctx.author.roles) if not r.is_default()), None
            )
            if not role:
                return await ctx.embed(
                    "You **don't** have any **roles** to display!", "warned"
                )

        members = [
            f"{member.mention} (`{member.id}`){' - **you**' if member == ctx.author else ''}"
            for member in role.members
        ]
        if not members:
            return await ctx.embed("No members have this role", "warned")

        embed = Embed(title=f"{len(members)} members in {role.name.capitalize()}")
        embed.set_author(
            name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url
        )

        await ctx.paginate(members, embed=embed)

    @group(aliases=("git", "gh"), invoke_without_command=True)
    async def github(self, ctx: Context, username: str) -> Message:
        """
        View a GitHub user's profile.
        """
        if "/" in username:
            return await self.github_repository(ctx, repository=username)

        async with ctx.typing():
            response = await self.bot.session.get(
                URL.build(
                    scheme="https",
                    host="api.github.com",
                    path=f"/users/{username}",
                ),
            )
            if response.status != 200:
                return await ctx.embed(
                    "The provided username was not found",
                    "warned",
                )

            data = await response.json()
            response = await self.bot.session.get(data["repos_url"])
            repos = await response.json()

        display_name = data.get("name", "") or data["login"]
        login = f" (@{data['login']})" if data.get("name") else ""

        embed = Embed(
            title=f"{display_name}{login}",
            url=data["html_url"],
        )
        embed.set_thumbnail(url=data["avatar_url"])

        info = []
        if data.get("bio"):
            info.append(data["bio"])
        if data.get("company"):
            info.append(
                f"🏢 [{data['company']}](http://google.com/search?q={data['company']})"
            )
        if data.get("location"):
            location = quote_plus(data["location"])
            info.append(
                f"🌎 [{data['location']}](http://maps.google.com/?q={location})"
            )

        if info:
            embed.add_field(
                name="Information",
                value="\n".join(info),
                inline=False,
            )

        if repos:
            repo_lines = []
            sorted_repos = sorted(
                repos, key=lambda x: x["stargazers_count"], reverse=True
            )[:3]
            for repo in sorted_repos:
                stars = repo["stargazers_count"]
                created = datetime.fromisoformat(
                    repo["created_at"].replace("Z", "+00:00")
                )
                repo_lines.append(
                    f"[`⭐ {stars}, {created:%m/%d/%y} {repo['name']}`]({repo['html_url']})"
                )

            embed.add_field(
                name=f"**Repositories ({data['public_repos']})**",
                value="\n".join(repo_lines),
                inline=False,
            )

        created_at = datetime.fromisoformat(data["created_at"].replace("Z", "+00:00"))
        embed.set_footer(
            text="Created on",
            icon_url="https://cdn.discordapp.com/emojis/843537056541442068.png",
        )
        embed.timestamp = created_at

        return await ctx.send(embed=embed)

    @github.command(name="repository", aliases=("repo",))
    async def github_repository(self, ctx: Context, *, repository: str) -> Message:
        """
        View a GitHub repository.
        """
        if "/" not in repository:
            if " " not in repository:
                return await ctx.embed(
                    "The provided repository was not found", "warned"
                )

            username, repository = repository.split(" ", 1)
        else:
            username, repository = repository.split("/", 1)

        async with ctx.typing():
            response = await self.bot.session.get(
                URL.build(
                    scheme="https",
                    host="api.github.com",
                    path=f"/repos/{username}/{repository}",
                ),
            )
            if response.status != 200:
                return await ctx.embed("The provided repository was not foundwarned")

            data = await response.json()
            response = await self.bot.session.get(
                data["commits_url"].replace("{/sha}", "")
            )
            commits = await response.json()

        embed = Embed(
            url=data["html_url"],
            title=data["full_name"],
            description=data["description"],
        )
        embed.set_thumbnail(url=data["owner"]["avatar_url"])
        embed.add_field(name="Stars", value=format(data["stargazers_count"], ","))
        embed.add_field(name="Forks", value=format(data["forks_count"], ","))
        embed.add_field(name="Issues", value=format(data["open_issues_count"], ","))
        if commits:
            embed.add_field(
                name="Latest Commits",
                value="\n".join(
                    [
                        f"[`{created_at:%m/%d/%Y}`]"
                        f"({commit['html_url']}) {shorten(commit['commit']['message'], 33)}"
                        for commit in commits[:6]
                        if (
                            created_at := datetime.fromisoformat(
                                commit["commit"]["author"]["date"]
                            )
                        )
                    ]
                ),
                inline=False,
            )

        return await ctx.send(embed=embed)

    @command(aliases=("cash", "ca"))
    async def cashapp(self, ctx: Context, user: CashAppUser) -> Message:
        """
        View a Cash App user's profile.
        """
        embed = Embed(
            url=user.url,
            title=f"{user.display_name} ${user.username}",
            description=f"-# Pay [${user.username}](https://cash.app/${user.username}) on Cash App",
        )
        embed.set_author(name=user.display_name, icon_url=user.avatar.url)
        embed.set_footer(
            text=f"Cash App",
            icon_url="https://upload.wikimedia.org/wikipedia/commons/thumb/c/c5/Square_Cash_app_logo.svg/1200px-Square_Cash_app_logo.svg.png",
        )
        if user.avatar:
            embed.set_thumbnail(url=user.avatar.url)
        else:
            embed.set_thumbnail(url=user.qr_code)

        return await ctx.send(embed=embed)

    @command(aliases=("snap",))
    async def snapchat(self, ctx: Context, *, username: str) -> Message:
        """
        View a Snapchat user's profile.
        """
        async with ctx.typing():
            try:
                snap = await Snapchat.from_username(username)
            except TypeError:
                return await ctx.embed(
                    f"[`{username}`](https://www.snapchat.com/add/{username}) is an invalid **snapchat** username",
                    "warned",
                )

        embed = Embed()
        embed.title = f"add {snap.display_name} (@{snap.username}) on Snapchat"
        embed.url = f"https://www.snapchat.com/add/{quote_plus(snap.username)}"

        if snap.bitmoji_url:
            embed.set_image(url=snap.bitmoji_url)

        embed.set_author(
            name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url
        )

        embed.set_footer(
            text="Snapchat",
            icon_url="https://assets.stickpng.com/images/580b57fcd9996e24bc43c536.png",
        )

        return await ctx.send(embed=embed)

    @command(aliases=["joined"])
    async def joins(self, ctx: Context) -> Message:
        """
        View members who joined today.
        """
        members = sorted(
            [
                m
                for m in ctx.guild.members
                if (datetime.now() - m.joined_at.replace(tzinfo=None)).total_seconds()
                < 3600 * 24
            ],
            key=lambda m: m.joined_at,
            reverse=True,
        )

        if not members:
            return await ctx.embed("No members joined today!", "warned")

        joins = [f"{m} - {format_dt(m.joined_at, style='R')}" for m in members]
        embed = Embed(title=f"{len(members)} joins today in {ctx.guild.name}")
        embed.set_author(
            name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url
        )

        return await ctx.paginate(joins, embed=embed)

    @command()
    async def emojis(self, ctx: Context) -> Message:
        """
        View the server emojis.
        """
        emojis = ctx.guild.emojis
        if not emojis:
            return await ctx.embed("This server doesn't have any emojis yet!", "warned")

        emojis = [f"{emoji} - **{emoji.name}** (`{emoji.id}`)" for emoji in emojis]
        embed = Embed(title=f"{len(emojis)} emojis in {ctx.guild.name}")
        embed.set_author(
            name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url
        )

        return await ctx.paginate(emojis, embed=embed)

    @command(aliases=["define"])
    async def dictionary(self, ctx: Context, *, word: str):
        """
        Look up a word definition from Wiktionary.
        """
        async with ctx.typing():
            result = await get_word_definition(word)

            if not result:
                raise CommandError(f"No definition found for **{word}**")

            entries = []
            embed = Embed(
                title=(
                    f"{result.word} • {result.pronunciation}"
                    if result.pronunciation
                    else result.word
                ),
                url=f"https://en.wiktionary.org/wiki/{quote_plus(result.word)}",
            )
            embed.set_author(
                name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url
            )
            embed.set_footer(
                icon_url="https://upload.wikimedia.org/wikipedia/commons/e/e7/Wiktionary-icon.png"
            )

            for definition in result.definitions:
                entries.append(f"{definition.text}")
                if definition.synonyms:
                    entries.append(f"*Synonyms: {definition.synonyms}*")

        return await ctx.paginate(entries, embed=embed, per_page=5)

    @command(aliases=["bans"])
    @has_permissions(ban_members=True)
    async def banlist(self, ctx: Context) -> Message:
        """
        View the server's banned users.
        """
        try:
            bans = [entry async for entry in ctx.guild.bans()]
        except:
            return await ctx.embed(
                "Unable to fetch bans or I can't view them!", "warned"
            )
        if not bans:
            return await ctx.embed("There's no one banned in this server!", "warned")

        entries = [
            f"{entry.user.name} (`{entry.user.id}`) - "
            f"{entry.reason[:80] + '...' if entry.reason and len(entry.reason) > 80 else entry.reason or 'No reason provided'}"
            for entry in bans
        ]

        embed = Embed(
            title=f"{len(bans)} banned members in {ctx.guild.name}"
        ).set_author(
            name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url
        )

        return await ctx.paginate(entries, embed=embed)

    @command()
    async def bots(self, ctx: Context) -> Message:
        """
        List all bots in the server.
        """
        bots = [member for member in ctx.guild.members if member.bot]

        if not bots:
            return await ctx.embed("There are no bots in this server!", "neutral")

        entries = [
            f"{bot.mention} (`{bot.id}`)"
            for bot in sorted(bots, key=lambda b: b.name.lower())
        ]

        embed = Embed(title=f"{len(bots)} bots in {ctx.guild.name}")
        embed.set_author(
            name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url
        )
        return await ctx.paginate(entries, embed=embed)

    @command()
    async def invites(self, ctx: Context) -> Message:
        """
        View the server's invites.
        """
        invites = await ctx.guild.invites()
        if not invites:
            return await ctx.embed("There are no invites in this server!", "warned")

        entries = [
            f"[{invite.code}]({invite.url}) by {f'**{invite.inviter.name}** (`{invite.inviter.id}`)' if invite.inviter else '**Unknown**'}"
            for invite in invites
        ]

        embed = Embed(title=f"{len(invites)} invites in {ctx.guild.name}")
        embed.set_author(
            name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url
        )
        return await ctx.paginate(entries, embed=embed)

    @group(invoke_without_command=True)
    async def boosters(self, ctx: Context) -> Message:
        """
        View the server's boosters.
        """
        boosters = ctx.guild.premium_subscribers
        if not boosters:
            return await ctx.embed(
                "There are **no** boosters in this server!", "warned"
            )

        entries = [
            f"{booster.mention} (`{booster.id}`) - {format_dt(booster.premium_since, 'R')} {'- **you**' if booster == ctx.author else ''}"
            for booster in sorted(boosters, key=lambda b: b.name.lower())
        ]

        embed = Embed(title=f"{len(boosters)} boosters in {ctx.guild.name}")
        embed.set_author(
            name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url
        )
        return await ctx.paginate(entries, embed=embed)

    @boosters.command(name="lost")
    async def boosters_lost(self, ctx: Context) -> Message:
        """
        View all lost boosters.
        """
        boosters_lost = [
            f"{user.mention} stopped {format_dt(record['ended_at'], 'R')} (lasted {short_timespan(record['lasted_for'])})"
            for record in await self.bot.pool.fetch(
                """
                SELECT *
                FROM boosters_lost
                WHERE guild_id = $1
                ORDER BY ended_at DESC
                """,
                ctx.guild.id,
            )
            if (user := self.bot.get_user(record["user_id"]))
        ]

        if not boosters_lost:
            return await ctx.embed("No boosters have been lost!", "warned")

        embed = Embed(title=f"{len(boosters_lost)} boosters lost in {ctx.guild.name}")
        embed.set_author(
            name=ctx.author.display_name,
            icon_url=ctx.guild.icon.url if ctx.guild.icon else None,
        )

        await ctx.paginate(boosters_lost, embed=embed)

    @command(
        aliases=("parse", "ce", "script"),
        example="{title: hi}",
    )
    @has_permissions(manage_messages=True)
    async def createembed(self, ctx: Context, *, script: Script) -> Message:
        """
        Create your own embed.
        """
        try:
            return await script.send(ctx)
        except HTTPException as exc:
            return await ctx.embed(
                "Something is wrong with your script",
                codeblock(exc.text),
                message_type="warned",
            )

    @command(aliases=("ui",))
    async def userinfo(
        self,
        ctx: Context,
        user: Member | User = parameter(default=lambda ctx: ctx.author),
    ) -> Message:
        """
        View information about a user.
        """

        embed = Embed(title=f"{user} {user.bot * '(BOT)'}")
        embed.set_thumbnail(url=user.display_avatar)
        embed.add_field(
            name="Created",
            value="\n".join(
                [
                    format_dt(user.created_at, "R"),
                    format_dt(user.created_at, "D"),
                ]
            ),
        )
        if isinstance(user, Member):
            joined_at = user.joined_at or datetime.utcnow()
            embed.add_field(
                name="Joined",
                value="\n".join(
                    [
                        format_dt(joined_at, "R"),
                        format_dt(joined_at, "D"),
                    ]
                ),
            )
            if user.premium_since:
                embed.add_field(
                    name="Boosted",
                    value="\n".join(
                        [
                            format_dt(user.premium_since, "R"),
                            format_dt(user.premium_since, "D"),
                        ]
                    ),
                )

            if roles := user.roles[1:]:
                embed.add_field(
                    name="Roles",
                    value=", ".join(role.mention for role in list(reversed(roles))[:5])
                    + (f" (+{len(roles) - 5})" if len(roles) > 5 else ""),
                    inline=False,
                )

            if (voice := user.voice) and voice.channel:
                members = len(voice.channel.members) - 1
                phrase = "Streaming inside" if voice.self_stream else "Inside"
                embed.description = (
                    (embed.description or "")
                    + f"🎙 {phrase} {voice.channel.mention} "
                    + (f"with {plural(members):other}" if members else "by themselves")
                )

            for activity_type, activities in groupby(
                user.activities,
                key=lambda activity: activity.type,
            ):
                activities = list(activities)
                if isinstance(activities[0], Spotify):
                    activity = activities[0]
                    embed.description = (
                        (embed.description or "")
                        + f"\n🎵 Listening to [**{activity.title}**]({activity.track_url}) by **{activity.artists[0]}**"
                    )

                elif isinstance(activities[0], Streaming):
                    embed.description = (
                        (embed.description or "")
                        + "\n🎥 Streaming "
                        + human_join(
                            [
                                f"[**{activity.name}**]({activity.url})"
                                for activity in activities
                                if isinstance(activity, Streaming)
                            ],
                            final="and",
                        )
                    )

                elif activity_type == ActivityType.playing:
                    embed.description = (
                        (embed.description or "")
                        + "\n🎮 Playing "
                        + human_join(
                            [f"**{activity.name}**" for activity in activities],
                            final="and",
                        )
                    )

                elif activity_type == ActivityType.watching:
                    embed.description = (
                        (embed.description or "")
                        + "\n📺 Watching "
                        + human_join(
                            [f"**{activity.name}**" for activity in activities],
                            final="and",
                        )
                    )

                elif activity_type == ActivityType.competing:
                    embed.description = (
                        (embed.description or "")
                        + "\n🏆 Competing in "
                        + human_join(
                            [f"**{activity.name}**" for activity in activities],
                            final="and",
                        )
                    )

        if user.mutual_guilds and user.id not in {
            *self.bot.owner_ids,
            self.bot.user.id,
        }:
            guilds: List[str] = []
            for guild in user.mutual_guilds:
                member = guild.get_member(user.id)
                if not member:
                    continue

                result = []
                if guild.owner_id == user.id:
                    result.append(ctx.config.emojis.badges.server_owner)

                elif member.guild_permissions.administrator:
                    result.append(ctx.config.emojis.badges.staff)

                if member.nick:
                    result.append(f"`{member.nick}` in")

                if guild.vanity_url:
                    result.append(f"[__{guild.name}__]({guild.vanity_url})")
                else:
                    result.append(f"__{guild.name}__")

                result.append(f"[`{guild.id}`]")
                guilds.append(" ".join(result))

            embed.add_field(
                name="Shared Servers",
                value="\n".join(guilds[:15]),
                inline=False,
            )

        return await ctx.send(embed=embed)


async def setup(bot: "Vesta") -> None:
    await bot.add_cog(Information(bot))
