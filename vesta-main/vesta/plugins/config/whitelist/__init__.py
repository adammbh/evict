from discord import Message, Member, User
from discord.ext.commands import Cog, has_permissions, group
from discord.errors import Forbidden

from typing import cast
from contextlib import suppress

from vesta.framework import Vesta, Context


class Whitelist(Cog):
    """
    Prevent users from joining your server unless they are whitelisted.
    """

    def __init__(self, bot: Vesta):
        self.bot = bot

    @group(name="whitelist", invoke_without_command=True)
    async def whitelist(self, ctx: Context):
        """
        Control who can and cannot join your server.
        """
        return await ctx.send_help(ctx.command)

    @whitelist.command(
        name="toggle",
        aliases=["switch"],
    )
    @has_permissions(manage_guild=True)
    async def whitelist_toggle(self, ctx: Context) -> Message:
        """
        Toggle the whitelist system.
        """
        status = cast(
            bool,
            await self.bot.pool.fetchval(
                """
                INSERT INTO whitelist (guild_id, status, user_id)
                VALUES ($1, TRUE, NULL)
                ON CONFLICT (guild_id) 
                WHERE user_id IS NULL
                DO UPDATE SET status = NOT whitelist.status
                RETURNING status
                """,
                ctx.guild.id,
            ),
        )

        return await ctx.embed(
            f"The **whitelist system** has been **{'enabled' if status else 'disabled'}**",
            "approved",
        )

    @whitelist.command(
        name="action",
        aliases=["setaction"],
    )
    @has_permissions(manage_guild=True)
    async def whitelist_action(self, ctx: Context, action: str):
        """
        Set the action to be taken when a user is not whitelisted.
        """
        if action not in ["kick", "ban"]:
            return await ctx.embed(
                "You can only set the action to `kick` or `ban`!", "warned"
            )

        await self.bot.pool.execute(
            """
            INSERT INTO whitelist (guild_id, action)
            VALUES ($1, $2)
            ON CONFLICT (guild_id)
            DO UPDATE SET action = $2
            """,
            ctx.guild.id,
            action,
        )
        return await ctx.embed(f"The action has been set to **{action}**.", "approved")

    @whitelist.command(
        name="add",
        aliases=["allow", "permit"],
    )
    @has_permissions(manage_guild=True)
    async def whitelist_add(self, ctx: Context, member: User):
        """
        Add a member to the whitelist.
        """
        record = await self.bot.pool.fetchrow(
            """
            SELECT * FROM whitelist 
            WHERE guild_id = $1 
            AND user_id = $2
            """,
            ctx.guild.id,
            member.id,
        )
        if record:
            return await ctx.embed(
                f"**{member.name}** is already on the whitelist!", "warned"
            )

        if not record:
            await self.bot.pool.execute(
                """
                INSERT INTO whitelist (guild_id, user_id)
                VALUES ($1, $2)
                """,
                ctx.guild.id,
                member.id,
            )
            return await ctx.embed(
                f"**{member.name}** has been added to the whitelist!", "approved"
            )

    @whitelist.command(
        name="remove",
        aliases=["revoke"],
    )
    @has_permissions(manage_guild=True)
    async def whitelist_remove(self, ctx: Context, user: Member | User):
        """
        Remove a member from the whitelist.
        """
        record = await self.bot.pool.fetchrow(
            """
            SELECT * FROM whitelist 
            WHERE guild_id = $1 
            AND user_id = $2
            """,
            ctx.guild.id,
            user.id,
        )
        if not record:
            return await ctx.embed(
                f"**{user.name}** is not on the whitelist!", "warned"
            )

        if isinstance(user, Member):
            await ctx.prompt(f"Would you like to kick **{user.name}** from the server?")
            try:
                await user.kick(
                    reason=f"User was removed from the whitelist. / {ctx.author}"
                )
            except Exception as e:
                return await ctx.embed(
                    f"An error occured while trying to kick **{user.name}**.", "warned"
                )

        if record:
            await self.bot.pool.execute(
                """
                DELETE FROM whitelist
                WHERE guild_id = $1
                AND user_id = $2
                """,
                ctx.guild.id,
                user.id,
            )
            return await ctx.embed(
                f"**{user.name}** has been removed from the whitelist!", "approved"
            )

    @Cog.listener("on_member_join")
    async def whitelist_check(self, member: Member):
        """
        Listener to check if a user is whitelisted.
        """
        record = await self.bot.pool.fetchrow(
            """
            SELECT status, action
            FROM whitelist
            WHERE guild_id = $1
            """,
            member.guild.id,
        )
        if not record or not record["status"]:
            return

        key = f"whitelist:attempts:{member.guild.id}:{member.id}"
        attempts = await self.bot.redis.incr(key)
        await self.bot.redis.expire(key, 60)

        if attempts > 3:
            with suppress(Forbidden):
                await member.ban(reason="Whitelist / Too many failed attempts.")
            return

        if record["action"] == "kick":
            with suppress(Forbidden):
                await member.kick(reason="Whitelist / User is not whitelisted.")

        elif record["action"] == "ban":
            with suppress(Forbidden):
                await member.ban(reason="Whitelist / User is not whitelisted.")
