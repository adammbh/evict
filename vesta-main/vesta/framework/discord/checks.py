from discord.ext import commands

from .context import Context


def roleplay_enabled():
    """
    Check if roleplay commands are enabled for the guild.
    """

    async def predicate(ctx: Context):
        record = await ctx.bot.pool.fetchval(
            """
            SELECT enabled
            FROM roleplay_enabled
            WHERE guild_id = $1
            """,
            ctx.guild.id,
        )
        if not record:
            await ctx.embed(
                f"Roleplay commands are not enabled for this server!\n"
                f"-# Enable using `{ctx.clean_prefix}roleplay true`",
                message_type="warned",
            )
            return False
        return True

    return commands.check(predicate)


def has_economy():
    """
    Check if a user has an economy account.
    """

    async def predicate(ctx: Context):
        record = await ctx.bot.pool.fetchrow(
            "SELECT user_id FROM economy WHERE user_id = $1", ctx.author.id
        )
        if not record:
            await ctx.embed(
                "You do not have an economy account! Use `start` to create one!",
                "warned",
            )
            return False
        return True

    return commands.check(predicate)

def has_company():
    """
    Check if the user owns a company in the server.
    """

    async def predicate(ctx: Context):
        business = await ctx.bot.pool.fetchrow(
            "SELECT 1 FROM businesses WHERE owner_id = $1 AND guild_id = $2",
            ctx.author.id, ctx.guild.id
        )
        if not business:
            await ctx.embed("You don't own a business here!", "warned")
            return False
        return True
    return commands.check(predicate)