from discord.ext.commands import group, has_permissions
from discord import Message
from discord.ext.commands import Cog, BadArgument

from vesta.framework import Vesta, Context


class Prefix(Cog):
    """
    Control the server prefix.
    """

    def __init__(self, bot: Vesta):
        self.bot = bot

    @group(invoke_without_command=True)
    async def prefix(self, ctx: Context) -> Message:
        """
        View the current server prefixes.
        """
        guild = await self.bot.pool.fetch(
            """
            SELECT DISTINCT prefix 
            FROM prefix 
            WHERE guild_id = $1
            """,
            ctx.guild.id,
        )

        prefix = [record["prefix"] for record in guild]
        await ctx.embed(
            f"The servers prefix is {', '.join(f'`{p}`' for p in prefix)}", "neutral"
        )

    @prefix.command(name="set", example=";")
    @has_permissions(manage_guild=True)
    async def prefix_set(self, ctx: Context, prefix: str) -> Message:
        """
        Set the server prefix.
        """
        if len(prefix) > 7:
            raise BadArgument("Prefix is too long!")

        if not prefix:
            return await ctx.embed(f"Prefix is too short!", "warned")

        check = await self.bot.pool.fetchrow(
            """
            SELECT * FROM prefix 
            WHERE guild_id = $1
            """,
            ctx.guild.id,
        )

        if check:
            await self.bot.pool.execute(
                """
                UPDATE prefix SET prefix = $1 
                WHERE guild_id = $2
                """,
                prefix,
                ctx.guild.id,
            )
        else:
            await self.bot.pool.execute(
                """
                INSERT INTO prefix (guild_id, prefix) 
                VALUES ($1, $2)
                """,
                ctx.guild.id,
                prefix,
            )
        return await ctx.embed(f"Guild prefix changed to `{prefix}`", "approved")

    @prefix.command(name="self", example="x")
    async def prefix_self(self, ctx: Context, prefix: str):
        """
        Set a custom prefix for yourself.
        """
        if len(prefix) > 7:
            raise BadArgument("Selfprefix is too long!")

        if not prefix:
            return await ctx.embed(f"Selfprefix is too short!", "warned")

        if prefix.lower() == "none":
            check = await self.bot.pool.fetchrow(
                """
                SELECT * FROM 
                selfprefix 
                WHERE user_id = $1
                """,
                ctx.author.id,
            )
            if check is not None:
                await ctx.prompt("Are you sure you want to remove your selfprefix?")
                await self.bot.pool.execute(
                    """
                    DELETE FROM selfprefix 
                    WHERE user_id = $1
                    """,
                    ctx.author.id,
                )

                return await ctx.embed("Removed your selfprefix.", "approved")

            elif check is None:
                return await ctx.embed("You dont have a self prefix!", "warned")
        else:
            result = await self.bot.pool.fetchrow(
                """
                SELECT * FROM 
                selfprefix WHERE 
                user_id = $1
                """,
                ctx.author.id,
            )

            if result is not None:
                await self.bot.pool.execute(
                    """
                    UPDATE selfprefix 
                    SET prefix = $1 
                    WHERE user_id = $2
                    """,
                    prefix,
                    ctx.author.id,
                )

            elif result is None:
                await self.bot.pool.execute(
                    """
                    INSERT INTO 
                    selfprefix 
                    VALUES ($1, $2)
                    """,
                    ctx.author.id,
                    prefix,
                )

            return await ctx.embed(f"Set your selfprefix to `{prefix}`.", "approved")
