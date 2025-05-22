from discord import Role, Member, Message
from discord.errors import HTTPException
from discord.ext.commands import BadArgument


from typing import Callable, List, Optional, Literal
from humanfriendly import format_timespan

from vesta.framework import Context
from vesta.framework.tools.conversion.discord import TouchableMember
from vesta.framework.tools.formatter import plural


class ModerationClass:
    """
    Class representing a role in the moderation system.
    """

    async def remove_role(self, ctx: Context, member: Member, role: Role):
        """
        Remove the specified role from the user.
        """
        if role in ctx.author.roles:
            await member.remove_roles(role)
            await ctx.embed(
                f"Role **{role.name}** removed from {member.mention}!", "approved"
            )
        else:
            await ctx.embed(
                f"{member.mention} does not have the role **{role.name}**!", "warned"
            )

    async def grant_role(self, ctx: Context, member: Member, role: Role):
        """
        Grant the specified role to the user.
        """
        if role not in ctx.author.roles:
            await member.add_roles(role)
            await ctx.embed(
                f"Role **{role.name}** granted to {member.mention}!", "approved"
            )
        else:
            await ctx.embed(
                f"{member.mention} already has the role **{role.name}**!", "warned"
            )
