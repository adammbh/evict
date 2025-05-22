from discord import User
from discord.ext.commands import Cog, command, has_permissions

from vesta.framework import Vesta, Context
from vesta.framework.discord.patches.permissions import is_donator


class Premium(Cog):
    def __init__(self, bot: Vesta):
        self.bot = bot

    @command()
    @is_donator()
    async def me(self, ctx: Context, amount: int = 100):
        """
        Purge messages sent by yourself.
        """
        await ctx.channel.purge(
            limit=amount, check=lambda m: m.author.id == ctx.author.id
        )


async def setup(bot: "Vesta") -> None:
    await bot.add_cog(Premium(bot))
