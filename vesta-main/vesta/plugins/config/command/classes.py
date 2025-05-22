from discord.ext.commands import Converter, Command
from discord.ext.commands.errors import BadArgument

from vesta.framework import Context


class CommandConverter(Converter):
    """
    Converts a string to a command object.
    """
    async def convert(self, ctx: Context, argument: str) -> Command:
        command = ctx.bot.get_command(argument)
        if command is None:
            raise BadArgument(f"Command `{argument}` not found!")

        elif command.qualified_name.startswith("command"):
            raise BadArgument("You cannot disable this command!")

        return command
