import discord

from logging import getLogger
from typing import Annotated

from discord import Message, Role
from discord.ui import View, Button
from discord.ext.commands import group, has_permissions, Cog

from .dynamicrolebutton import DynamicRoleButton
from vesta.framework import Vesta, Context
from vesta.framework.tools.conversion import StrictRole

log = getLogger("vesta/buttonroles")


class Buttons(Cog):
    """
    Allow members to assign roles to themselves using buttons.
    """
    def __init__(self, bot: Vesta) -> None:
        self.bot = bot

    @group(
        name="rolebuttons",
        invoke_without_command=True,
    )
    @has_permissions(manage_messages=True)
    async def rolebutton(self, ctx: Context):
        """
        Allow members to assign roles to themselves using buttons.
        """
        return await ctx.send_help(ctx.command)

    @has_permissions(manage_messages=True)
    @rolebutton.command(name="add")
    async def rolebutton_add(
        self,
        ctx: Context,
        message: Message,
        emoji: str,
        role: Annotated[
            Role,
            StrictRole(check_dangerous=True),
        ],
    ):
        """
        Add a reaction button to a message.
        """
        if message.author.id != self.bot.user.id:
            return await ctx.embed(
                f"I can only add role buttons to my own messages.\n"
                f"-# You can create an embed using `{ctx.clean_prefix}createembed (code)` and add the button there.",
                message_type="warned",
            )

        if role.is_premium_subscriber():
            return await ctx.embed(
                "I cant assign integrated roles to users!",
                message_type="warned"    
            )

        view = View()

        for component in message.components:
            if isinstance(component, discord.components.ActionRow):
                for button in component.children:
                    if button.custom_id == f"RB:{message.id}:{role.id}":
                        return await ctx.embed(
                            f"{role.mention} is already assigned to this message!"
                        )

                    if button.custom_id.startswith("RB"):
                        view.add_item(
                            DynamicRoleButton(
                                message_id=button.custom_id.split(":")[1],
                                role_id=button.custom_id.split(":")[2],
                                emoji=button.emoji,
                            )
                        )

                    else:
                        view.add_item(
                            Button(
                                style=button.style,
                                label=button.label,
                                emoji=button.emoji,
                                url=button.url,
                                disabled=button.disabled,
                            )
                        )
        view.add_item(
            DynamicRoleButton(message_id=message.id, role_id=role.id, emoji=emoji)
        )
        await message.edit(view=view)
        return await ctx.embed(
            f"Added {role.mention} to [**message**]({message.jump_url})",
            message_type="approved",
        )

    @rolebutton.command(name="remove")
    @has_permissions(manage_messages=True)
    async def rolebutton_remove(
        self, ctx: Context, message: Message, role: Role
    ):
        """
        Remove a reaction button from a message.
        """
        if message.author.id != self.bot.user.id:
            return await ctx.embed(
                f"I can only remove buttons from my own messages!\n" 
                f"-# You can create an embed using `{ctx.clean_prefix}createembed (code)` and add the button there.",
                message_type="warned",
            )
        
        view = View()
        for component in message.components:
            if isinstance(component, discord.components.ActionRow):
                for button in component.children:
                    if button.custom_id == f"RB:{message.id}:{role.id}":
                        continue
                    if button.custom_id.startswith("RB"):
                        view.add_item(
                            DynamicRoleButton(
                                message_id=message.id,
                                role_id=role.id,
                                emoji=button.emoji,
                            )
                        )
                    else:
                        view.add_item(
                            discord.ui.Button(
                                style=button.style,
                                label=button.label,
                                emoji=button.emoji,
                                url=button.url,
                                disabled=button.disabled,
                            )
                        )

        await message.edit(view=view)
        return await ctx.embed(
            f"Removed {role.mention} from [**message**]({message.jump_url})",
            message_type="approved",
        )
