from discord import (
    Message,
    Embed,
    Member,
)
from discord.ext.commands import Cog, command, has_permissions, cooldown, group

from random import randint

from vesta.framework import Vesta, Context
from vesta.framework.tools.conversion import TouchableMember

from .media import Media


class Fun(Media, Cog):
    def __init__(self, bot: Vesta):
        self.bot = bot

    @command(aliases=["mock"])
    @has_permissions(manage_messages=True, manage_webhooks=True)
    @cooldown(1, 5)
    async def impersonate(
        self, ctx: Context, member: Member, *, message: str
    ) -> Message:
        """
        Impersonate a member.
        """
        try:
            await ctx.message.delete()
        except Exception:
            return await ctx.embed(
                "I don't have permission to delete messages!", "warned"
            )

        webhook = await ctx.channel.create_webhook(
            name=member.display_name, reason=f"{ctx.author} / impersonate"
        )

        await webhook.send(
            content=message,
            username=member.display_name,
            avatar_url=member.display_avatar,
        )
        return await webhook.delete(reason=f"{ctx.author} / impersonate")

    @group(name="uwulock", aliases=["uwu"], invoke_without_command=True)
    @has_permissions(manage_messages=True)
    async def uwulock(self, ctx: Context, member: Member):
        """
        Automatically uwuify a members messages.
        """
        if isinstance(member, Member):
            await TouchableMember().check(ctx, member)

        record = await self.bot.pool.fetchrow(
            """
            SELECT * FROM uwulock 
            WHERE guild_id = $1 
            AND user_id = $2
            """,
            ctx.guild.id,
            member.id,
        )
        if record:
            await ctx.prompt(
                f"Would you like to remove **{member.name}** from the uwulock?"
            )
            await self.bot.pool.execute(
                """
                DELETE FROM uwulock 
                WHERE guild_id = $1 
                AND user_id = $2
                """,
                ctx.guild.id,
                member.id,
            )
            return await ctx.embed(
                f"**{member.name}** has been removed from the uwulock!", "approved"
            )

        if not record:
            await self.bot.pool.execute(
                """
                INSERT INTO uwulock (guild_id, user_id)
                VALUES ($1, $2)
                """,
                ctx.guild.id,
                member.id,
            )
            return await ctx.embed(
                f"**{member.name}** has been added to the uwulock!", "approved"
            )

    @group(name="shutup", aliases=["stfu"], invoke_without_command=True)
    @has_permissions(manage_messages=True)
    async def shutup(self, ctx: Context, member: Member):
        """
        Automatically delete a members messages.
        """
        if isinstance(member, Member):
            await TouchableMember().check(ctx, member)

        record = await self.bot.pool.fetchrow(
            """
            SELECT * FROM shutup 
            WHERE guild_id = $1 
            AND user_id = $2
            """,
            ctx.guild.id,
            member.id,
        )
        if record:
            await ctx.prompt(f"Would you like to remove **{member.name}** from shutup?")
            await self.bot.pool.execute(
                """
                DELETE FROM shutup 
                WHERE guild_id = $1 
                AND user_id = $2
                """,
                ctx.guild.id,
                member.id,
            )
            return await ctx.embed(
                f"**{member.name}** has been removed from shutup!", "approved"
            )

        if not record:
            await self.bot.pool.execute(
                """
                INSERT INTO shutup (guild_id, user_id)
                VALUES ($1, $2)
                """,
                ctx.guild.id,
                member.id,
            )
            return await ctx.embed(
                f"**{member.name}** has been added to shutup!", "approved"
            )

    @command()
    async def howretarded(self, ctx: Context, member: Member = None) -> Message:
        """
        Check how retarded a member is.
        """
        member = member or ctx.author
        return await ctx.embed(
            f"**{member.display_name}** is ``{randint(0, 100)}%`` retarded.", "neutral"
        )

    @command()
    async def howgay(self, ctx: Context, member: Member = None) -> Message:
        """
        Check how gay a member is.
        """
        member = member or ctx.author
        return await ctx.embed(
            f"**{member.display_name}** is ``{randint(0, 100)}%`` gay.", "neutral"
        )

    @command()
    async def howlesbian(self, ctx: Context, member: Member = None) -> Message:
        """
        Check how much of a lesbian a member is.
        """
        member = member or ctx.author
        return await ctx.embed(
            f"**{member.display_name}** is ``{randint(0, 100)}%`` lesbian.", "neutral"
        )

    @command(aliases=["dih"])
    async def penis(self, ctx: Context, member: Member = None) -> Message:
        """
        Check a members penis size.
        """
        member = member or ctx.author
        penis = "===================="
        embed = Embed(
            title=f"{member.display_name}'s dih",
            description=f"8{penis[randint(1, 20) :]}D",
        )
        return await ctx.send(embed=embed)


async def setup(bot: "Vesta") -> None:
    await bot.add_cog(Fun(bot))
