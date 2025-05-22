from __future__ import annotations

import re
import copy
from typing import Any, Dict, List, Optional, TypedDict, Union, cast, Callable
from datetime import datetime, timedelta
from cashews import cache

from discord import (
    ButtonStyle,
    Color,
    Embed,
    HTTPException,
    Interaction,
    Message,
    Permissions,
    SelectOption,
    User,
    Member,
)
from discord.ext import commands
from discord.ext.commands import Cog, Command, Group, BadArgument, Converter, command
from discord.ui import Select, View
from discord.ext.commands.flags import Flag, MISSING, FlagsMeta
from discord.utils import oauth_url

from vesta.framework.tools.formatter import short_timespan, shorten
# from vesta.framework.tools import FlagConverter

from vesta.framework import Vesta, Context
from vesta.framework.pagination import Paginator


RESTRICTED_CATEGORIES = ["owner", "jishaku", "errors", "developer", "listeners"]


# def add_flag_formatting(annotation: FlagConverter, embed: Embed) -> None:
#    flags = annotation.get_flags()
#
#    def format_flag(name: str, flag: Flag) -> str:
#        default = flag.default
#        argument = ""
#        if default is not MISSING:
#            if isinstance(default, timedelta):
#                argument = f"={short_timespan(default)}"
#            elif not isinstance(default, bool):
#                argument = f"={default}"
#        return f"`--{name}{argument}`: {flag.description}"
#
#    optional = [
#        format_flag(name, flag)
#        for name, flag in flags.items()
#        if flag.default is not MISSING
#    ]
#    required = [
#        format_flag(name, flag)
#        for name, flag in flags.items()
#        if flag.default is MISSING
#    ]
#
#    if required:
#        embed.add_field(name="Required Flags", value="\n".join(required), inline=True)
#    if optional:
#        embed.add_field(name="Optional Flags", value="\n".join(optional), inline=True)
#


def get_syntax(command: Command) -> str:
    """
    Generates the syntax string for a command based on its parameters and usage.
    """
    if command.usage:
        return f"{command.qualified_name} {command.usage}".strip()

    params = [
        f"<{name}>" if param.default == param.empty else f"[{name}]"
        for name, param in command.clean_params.items()
    ]
    return f"{command.qualified_name} {' '.join(params)}".strip()


@cache(ttl="1h")
async def get_param_examples() -> Dict[str, str]:
    """
    Generates a dictionary of example values for common command parameters.
    """
    return {
        "user": "@herry",
        "member": "@herry",
        "target": "@herry",
        "author": "@herry",
        "users": "@user1 @user2",
        "members": "@member1 @member2",
        "mentions": "@user1 @user2",
        "role": "@role",
        "roles": "@role1 @role2",
        "role_name": "Moderator",
        "channel": "#channel",
        "channels": "#channel1 #channel2",
        "category": "General",
        "thread": "#thread",
        "reason": "broke rules",
        "content": "your message here",
        "text": "some text",
        "title": "my title",
        "description": "detailed description",
        "name": "boosters",
        "new_name": "admins",
        "message": "hello world",
        "query": "search term",
        "duration": "7d",
        "time": "24h",
        "interval": "30m",
        "delay": "10s",
        "history": "30d",
        "timeout": "1h",
        "date": "2023-04-15",
        "amount": "5",
        "count": "10",
        "limit": "25",
        "number": "3",
        "pages": "2",
        "max": "100",
        "min": "1",
        "quantity": "7",
        "image": "image.png",
        "attachment": "file.txt",
        "file": "document.pdf",
        "avatar": "profile.jpg",
        "banner": "banner.png",
        "command": "help",
        "cmd": "ban",
        "color": "#ff0000",
        "emoji": "😄",
        "url": "https://example.com",
        "event": "message",
        "event_names": "join leave",
        "assign_role": "@member_role",
        "prefix": "!",
        "mode": "strict",
        "filter": "nsfw",
        "position": "2",
        "action": "kick",
        "level": "3",
        "settings": "notifications",
        "permission": "manage_messages",
        "id": "123456789...",
        "language": "english",
        "timezone": "UTC",
    }


async def generate_examples(command: Command) -> List[str]:
    """
    Generates example usage strings for a command based on its parameters and their types.
    """
    if not command.clean_params:
        return []

    ex = f"{command.qualified_name} "
    param_examples = await get_param_examples()

    for name, param in command.clean_params.items():
        name_lower = name.lower()
        param_type = (
            str(param.annotation).lower() if param.annotation != param.empty else ""
        )

        if name_lower in param_examples:
            ex += f"{param_examples[name_lower]} "
            continue

        matched = False
        for key, value in param_examples.items():
            if key in name_lower:
                ex += f"{value} "
                matched = True
                break

        if matched:
            continue

        if any(t in param_type for t in ("user", "member")):
            ex += "@harry "
        elif "role" in param_type:
            ex += "@homies "
        elif any(t in param_type for t in ("channel", "textchannel")):
            ex += "#general "
        elif any(t in param_type for t in ("guild", "server")):
            ex += "stmpsupport "
        elif any(t in param_type for t in ("bool", "bool)")):
            ex += "yes "
        elif any(t in param_type for t in ("int", "float", "number")):
            ex += "5 "
        elif any(t in param_type for t in ("str", "string")):
            ex += f"{name} "
        else:
            ex += f"{name} "

    return [ex.strip()]


async def get_example(command: Command) -> Optional[str]:
    """
    Generates an example usage string for a command based on its attributes and parameters.
    """
    if hasattr(command, "example") and command.example:
        return f"{command.qualified_name} {command.example}"

    if command.usage and "example:" in command.usage.lower():
        if example_match := re.search(
            r"example:?\s*(.*?)(?:\n|$)", command.usage, re.IGNORECASE
        ):
            return f"{command.qualified_name} {example_match.group(1).strip()}"

    if command.help and "example:" in command.help.lower():
        if example_match := re.search(
            r"example:?\s*(.*?)(?:\n|$)", command.help, re.IGNORECASE
        ):
            return f"{command.qualified_name} {example_match.group(1).strip()}"

    if generated := await generate_examples(command):
        return generated[0]

    return None


async def interaction_check(interaction: Interaction, user: User, ctx: Context) -> bool:
    """
    Checks if the interaction is from the original author of the context.
    """
    if interaction.user.id != ctx.author.id:
        await interaction.warn(
            "You're not the **author** of this embed!", ephemeral=True
        )
    return interaction.user.id == ctx.author.id


class EvictCategorySelect(Select):
    def __init__(self, categories: Dict[str, Cog]) -> None:
        self.categories = categories
        self.embed = None
        options = [SelectOption(label=key, value=key) for key in categories]
        super().__init__(placeholder="Select a Category", options=options)

    async def callback(self, interaction: Interaction) -> None:
        """
        Callback for when a category is selected from the dropdown.
        """
        if not self.embed:
            if interaction.message and interaction.message.embeds:
                self.embed = interaction.message.embeds[0].copy()
            else:
                return

        if not (category := self.categories.get(self.values[0])):
            return

        groups = []
        commands = []

        for command in category.walk_commands():
            if (
                isinstance(command, Group)
                and command.name not in groups
                and command.parent is None
            ):
                groups.append(command.name)
                commands.append(command.name)
            elif not isinstance(command, Group) and command.parent is None:
                commands.append(command.name)

        embed = copy.deepcopy(self.embed)
        embed.clear_fields()
        embed.title = f"`Category: ` {category.__cog_name__}\n`Commands: ` {len(set(category.walk_commands()))}"

        description = category.__doc__ or ""

        cmds_display = (
            ", ".join(f"{name}*" if name in groups else name for name in commands)
            or "No Commands Present"
        )

        embed.description = f"{description}\n```{cmds_display}```"
        embed.set_footer(text="")
        await interaction.response.edit_message(embed=embed)


class Selector(View):
    def __init__(self, ctx: Context, select: EvictCategorySelect) -> None:
        super().__init__(timeout=300)
        self.add_item(select)
        self.ctx = ctx

    async def interaction_check(self, interaction: Interaction) -> bool:
        """
        Checks if the interaction is from the original author of the context.
        """
        if interaction.user.id != self.ctx.author.id:
            await interaction.embed("You're not the **author** of this embed!")
        return interaction.user.id == self.ctx.author.id


class HelpMenu:
    def __init__(self, bot: Vesta) -> None:
        self.bot = bot

    async def send(self, ctx: Context, command: str = None) -> Message:
        """
        Sends help for a specific command or the main help menu if no command is specified.
        """
        return (
            await self.send_command_help(ctx, command)
            if command
            else await self.send_main_help(ctx)
        )

    async def send_main_help(self, ctx: Context) -> Message:
        """
        Sends the main help menu with a list of categories and commands.
        """
        embed = Embed(description="> `[ ] = optional` \n> `< > = required`")
        embed.set_author(
            name=self.bot.user.name, icon_url=self.bot.user.display_avatar.url
        )

        invite_url = oauth_url(self.bot.user.id, permissions=Permissions(permissions=8))
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        embed.add_field(
            name="",
            value=(
                f">>> -#  [Invite]({invite_url})\n"
                f"-#  [Support](https://discord.gg/evict)\n"
                f"-# [View on Web](https://evict.bot/)"
            ),
            inline=False,
        )

        categories = {
            name: cog
            for name, cog in self.bot.cogs.items()
            if name.lower() not in RESTRICTED_CATEGORIES
        }

        view = Selector(ctx, EvictCategorySelect(categories))
        return await ctx.send(embed=embed, view=view)

    async def send_command_help(self, ctx: Context, command: str) -> Message:
        """
        Sends help for a specific command or command group.
        """
        if not (command_obj := self.bot.get_command(command)):
            return await ctx.embed(
                f"Command `{shorten(command)}` does **not** exist", "warned"
            )

        if (
            command_obj.cog_name
            and command_obj.cog_name.lower() in RESTRICTED_CATEGORIES
        ):
            return await ctx.embed(
                f"Command `{shorten(command)}` does **not** exist", "warned"
            )

        if isinstance(command_obj, Group) and command_obj.commands:
            return await self.send_group_help(
                ctx, command_obj, list(command_obj.commands)
            )

        return await self.send_single_command_help(ctx, command_obj)

    async def send_single_command_help(self, ctx: Context, command: Command) -> Message:
        """
        Sends help for a single command, including its description, syntax, and permissions.
        """
        module_name = command.cog_name or "None"
        embed = Embed(description=f"> {command.help}" or "No description available")
        embed.set_author(
            name=f"{self.bot.user.name} help", icon_url=self.bot.user.display_avatar.url
        )
        embed.title = (
            f"` Command:  ` {command.qualified_name}\n` Module:   ` {module_name}"
        )

        example = await get_example(command)
        syntax_example = "```Ruby\nSyntax: " + get_syntax(command)
        if example:
            syntax_example += f"\nExample: {example}"
        syntax_example += "```"

        embed.add_field(name="", value=syntax_example, inline=False)

        if perms := getattr(command, "permissions", []):
            embed.add_field(
                name="Permissions",
                value=", ".join(perm.replace("_", " ").title() for perm in perms),
                inline=True,
            )

        # for param in command.clean_params.values():
        #    if isinstance(param.annotation, FlagsMeta):
        #        add_flag_formatting(param.annotation, embed)

        aliases = ", ".join(command.aliases) if command.aliases else "None"
        embed.set_footer(
            text=f"Aliases: {aliases}", icon_url=ctx.author.display_avatar.url
        )

        return await ctx.reply(embed=embed)

    async def send_group_help(
        self, ctx: Context, group: Group, commands: List[Command]
    ) -> Message:
        """
        Sends help for a command group, including all its subcommands.
        """
        all_commands = [group]
        all_commands.extend(
            cmd
            for cmd in group.walk_commands()
            if cmd.parent and cmd.parent.qualified_name == group.qualified_name
        )

        embeds = []
        for command in all_commands:
            module_name = command.cog_name or "None"
            embed = Embed(description=f"> {command.help}" or "No description available")
            embed.set_author(
                name=f"{self.bot.user.name} help",
                icon_url=self.bot.user.display_avatar.url,
            )
            embed.title = (
                f"` Command:  ` {command.qualified_name}\n` Module:   ` {module_name}"
            )

            example = await get_example(command)
            if not example and isinstance(command, Group):
                example = command.qualified_name

            syntax_example = "```Ruby\nSyntax: " + get_syntax(command)
            if example:
                syntax_example += f"\nExample: {example}"
            syntax_example += "```"

            embed.add_field(name="", value=syntax_example, inline=False)

            if perms := getattr(command, "permissions", []):
                embed.add_field(
                    name="Permissions",
                    value=", ".join(perm.replace("_", " ").title() for perm in perms),
                    inline=True,
                )

            # for param in command.clean_params.values():
            #    if isinstance(param.annotation, FlagsMeta):
            #        add_flag_formatting(param.annotation, embed)

            aliases = ", ".join(command.aliases) if command.aliases else "None"
            embed.set_footer(
                text=f"Module: {module_name} • Aliases: {aliases}",
                icon_url=ctx.author.display_avatar.url,
            )
            embeds.append(embed)

        paginator = Paginator(ctx, embeds)
        return await paginator.start()


class Help(Cog):
    def __init__(self, bot: Vesta):
        self.bot = bot
        self.menu = HelpMenu(bot)

    @command(aliases=["h"], example="ban")
    async def help(self, ctx: Context, *, command: str = None) -> None:
        """
        View help for a command or category.
        """
        await self.menu.send(ctx, command)
