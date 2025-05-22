from typing import List, cast
from asyncpg import UniqueViolationError
from xxhash import xxh64_hexdigest

from discord import Embed, HTTPException, Message, NotFound
from discord.ext.commands import Cog, Range, group, has_permissions

from vesta.framework import Context, Vesta
from vesta.framework.tools.formatter import plural

class Reaction(Cog):
    """
    Automatically react to messages.
    """
    def __init__(self, bot: Vesta) -> None:
        self.bot = bot

    @group(
        aliases=["react", "rt"],
        invoke_without_command=True,
    )
    @has_permissions(manage_messages=True)
    async def reaction(self, ctx: Context) -> Message:
        """
        Automatically react to messages.
        """
        return await ctx.send_help(ctx.command)

    @reaction.command(
        name="add",
        aliases=["create"],
        example="emoji hi",
    )
    @has_permissions(manage_messages=True)
    async def reaction_add(
        self,
        ctx: Context,
        emoji: str,
        *,
        trigger: Range[str, 1, 50],
    ) -> Message:
        """
        Add a new reaction trigger.
        """
        try:
            await ctx.message.add_reaction(emoji)
        except (HTTPException, TypeError):
            return await ctx.embed(
                "I couldn't add the reaction to the message!",
                message_type="warned",
            )

        records = cast(
            int,
            await self.bot.pool.fetchval(
                """
                SELECT COUNT(*)
                FROM reaction_trigger
                WHERE guild_id = $1
                AND trigger = LOWER($2)
                """,
                ctx.guild.id,
                trigger,
            ),
        )
        if records >= 3:
            return await ctx.embed(
                "You can't have more than `3` reactions per trigger!",
                message_type="warned",
            )
        
        try:
            await self.bot.pool.execute(
                """
                INSERT INTO reaction_trigger (
                    guild_id,
                    trigger,
                    emoji
                ) VALUES (
                    $1,
                    LOWER($2),
                    $3
                )
                """,
                ctx.guild.id,
                trigger,
                emoji,
            )
        except UniqueViolationError:
            return await ctx.embed(
                f"A reaction trigger with {emoji} for **{trigger}** already exists!",
                message_type="warned",
            )

        return await ctx.embed(
            f"Now reacting with {emoji} for **{trigger}**",
            message_type="approved",
        )

    @reaction.command(
        name="remove",
        aliases=["delete", "del", "rm"],
        example="emoji hi",
    )
    @has_permissions(manage_messages=True)
    async def reaction_remove(
        self,
        ctx: Context,
        emoji: str,
        *,
        trigger: Range[str, 1, 50],
    ) -> Message:
        """
        Remove a reaction trigger.
        """
        result = await self.bot.pool.execute(
            """
            DELETE FROM reaction_trigger
            WHERE guild_id = $1
            AND trigger = LOWER($2)
            """,
            ctx.guild.id,
            trigger,
        )
        if result == "DELETE 0":
            return await ctx.embed(
                f"No reaction trigger with {emoji} for **{trigger}** exists!",
                message_type="warned",
            )

        return await ctx.embed(
            f"No longer reacting with {emoji} for **{trigger}**",
            message_type="approved",
        )

    @reaction.command(
        name="clear",
        aliases=["clean", "reset"],
    )
    @has_permissions(manage_messages=True)
    async def reaction_clear(self, ctx: Context) -> Message:
        """
        Remove all reaction triggers.
        """
        await ctx.prompt(
            "Are you sure you want to remove all reaction triggers?\n",
            "-# This is **irreversible**!",
        )

        result = await self.bot.pool.execute(
            """
            DELETE FROM reaction_trigger
            WHERE guild_id = $1
            """,
            ctx.guild.id,
        )
        if result == "DELETE 0":
            return await ctx.embed(
                "No reaction triggers exist for this server!",
                message_type="warned",
            )

        return await ctx.embed(
            f"Successfully removed {plural(result, md='`'):reaction trigger}",
            message_type="approved",
        )

    @reaction.command(
        name="list",
        aliases=["ls"],
    )
    @has_permissions(manage_guild=True)
    async def reaction_list(self, ctx: Context) -> Message:
        """
        View all reaction triggers.
        """
        triggers = [
            f"**{record['trigger']}** | {', '.join(record['emojis'])}"
            for record in await self.bot.pool.fetch(
                """
                SELECT
                    trigger,
                    ARRAY_AGG(emoji) AS emojis
                FROM reaction_trigger
                WHERE guild_id = $1
                GROUP BY trigger
                """,
                ctx.guild.id,
            )
        ]
        if not triggers:
            return await ctx.embed(
                "No reaction triggers exist for this server!",
                message_type="warned",
            )

        return await ctx.paginate(
                entries=triggers,
                embed=Embed(
                title=f"{len(triggers)} Reaction Trigger{'s' if len(triggers) > 1 else ''}"
            ),
        )
    
    @Cog.listener("on_message_without_command")
    async def reaction_listener(self, ctx: Context) -> None:
        """
        Automatically react to a trigger.
        """
        reactions = cast(
            List[str],
            await self.bot.pool.fetchval(
                """
                SELECT ARRAY_AGG(emoji)
                FROM reaction_trigger
                WHERE guild_id = $1
                AND LOWER($2) LIKE '%' || LOWER(trigger) || '%'
                GROUP BY trigger
                """,
                ctx.guild.id,
                ctx.message.content,
            ),
        )
        if not reactions:
            return

        KEY = xxh64_hexdigest(f"reactions:{ctx.author.id}")
        if await self.bot.redis.ratelimited(KEY, 1, 3):
            return

        scheduled_deletion: List[str] = []
        for reaction in reactions:
            try:
                await ctx.message.add_reaction(reaction)
            except NotFound:
                scheduled_deletion.append(reaction)
            except (HTTPException, TypeError):
                ...

        if scheduled_deletion:
            await self.bot.pool.execute(
                """
                DELETE FROM reaction_trigger
                WHERE guild_id = $1
                AND emoji = ANY($2::TEXT[])
                """,
                ctx.guild.id,
                scheduled_deletion,
            )