from discord import TextChannel, Member
from discord.ext.commands import Cog, has_permissions, group

from datetime import datetime
from contextlib import suppress

from vesta.framework import Vesta, Context

poj_cache = {}


class PingOnJoin(Cog):
    """
    Mention new members when they join the server.
    """

    def __init__(self, bot: Vesta):
        self.bot = bot

    @group(invoke_without_command=True, aliases=["poj"])
    async def pingonjoin(self, ctx: Context):
        """
        Mention new members when they join the server.
        """
        await ctx.send_help(ctx.command)

    @pingonjoin.command(name="add")
    @has_permissions(manage_guild=True)
    async def poj_add(self, ctx: Context, *, channel: TextChannel):
        """
        Add a channel to mention new members upon join.
        """
        check = await self.bot.pool.fetchrow(
            """
            SELECT * FROM pingonjoin 
            WHERE guild_id = $1 
            AND channel_id = $2
            """,
            ctx.guild.id,
            channel.id,
        )

        if check is not None:
            return await ctx.embed(
                message=f"{channel.mention} is already mentioning new members!",
                message_type="warned",
            )

        elif check is None:
            await self.bot.pool.execute(
                """
                INSERT INTO pingonjoin 
                VALUES ($1, $2)
                """,
                channel.id,
                ctx.guild.id,
            )

        return await ctx.embed(
            message=f"Now mentioning new members in {channel.mention}",
            message_type="approved",
        )

    @pingonjoin.command(name="remove")
    @has_permissions(manage_guild=True)
    async def poj_remove(self, ctx: Context, *, channel: TextChannel = None):
        """
        Remove a channel from mentioning new members upon join.
        """
        if channel is not None:
            check = await self.bot.pool.fetchrow(
                """
                SELECT * FROM pingonjoin 
                WHERE guild_id = $1 
                AND channel_id = $2
                """,
                ctx.guild.id,
                channel.id,
            )

            if check is None:
                return await ctx.embed(
                    message=f"{channel.mention} is not added as an pingonjoin channel!",
                    message_type="warned",
                )

            elif check is not None:
                await self.bot.pool.execute(
                    """
                    DELETE FROM pingonjoin 
                    WHERE guild_id = $1 
                    AND channel_id = $2
                    """,
                    ctx.guild.id,
                    channel.id,
                )

            return await ctx.embed(
                message=f"No longer mentioning new members in {channel.mention}",
                message_type="approved",
            )

        check = await self.bot.pool.fetch(
            """
            SELECT * FROM pingonjoin 
            WHERE guild_id = $1
            """,
            ctx.guild.id,
        )

        if check is None:
            return await ctx.embed("There is no channel added!", "warned")

        elif check is not None:
            await ctx.prompt(
                "Are you sure you want to remove all channels from pingonjoin?"
            )
            await self.bot.pool.execute(
                """
                DELETE FROM pingonjoin 
                WHERE guild_id = $1
                """,
                ctx.guild.id,
            )

        return await ctx.embed(
            message="No longer mentioning new members in any channel!",
            message_type="approved",
        )

    @Cog.listener("on_member_join")
    async def pingonjoin_listener(self, member: Member):
        """
        Listen for new members joining the server
        and mention them.
        """
        if member.bot:
            return

        cache_key = f"poj:{member.guild.id}"
        channels = await self.bot.redis.get(cache_key)

        if not channels:
            records = await self.bot.pool.fetch(
                """
                SELECT channel_id 
                FROM pingonjoin 
                WHERE guild_id = $1
                """,
                member.guild.id,
            )
            channels = [record["channel_id"] for record in records]
            await self.bot.redis.set(cache_key, channels, ex=60)

        recent_joins = [
            m
            for m in member.guild.members
            if (datetime.now() - m.joined_at.replace(tzinfo=None)).total_seconds() < 180
        ]

        for channel_id in channels:
            channel = member.guild.get_channel(int(channel_id))
            if not channel:
                await self.bot.pool.execute(
                    """
                    DELETE FROM pingonjoin 
                    WHERE guild_id = $1 
                    AND channel_id = $2
                    """,
                    member.guild.id,
                    channel_id,
                )
                continue

            with suppress(Exception):
                if len(recent_joins) < 10:
                    await channel.send(member.mention, delete_after=6)
                else:
                    poj_cache.setdefault(str(channel.id), []).append(member.mention)
                    if len(poj_cache[str(channel.id)]) >= 10:
                        await channel.send(
                            " ".join(poj_cache[str(channel.id)]), delete_after=6
                        )
                        poj_cache[str(channel.id)] = []
