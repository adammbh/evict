from discord import Interaction, ButtonStyle
from discord.ui import View, Button, button
from discord.ext.commands import Converter, BadArgument, Context


class OwnerID(View):
    """
    View for Owner ID confirmation with multiple buttons.
    """

    def __init__(self, response_messages: dict):
        super().__init__(timeout=None)
        self.response_messages = response_messages
        self.value = None

    @button(label="Owner ID", style=ButtonStyle.grey)
    async def ownerid(self, interaction: Interaction, button: Button):
        """
        Retrieve the owner ID of the guild and send it as a response.
        """
        await interaction.response.send_message(
            self.response_messages.get("owner-id", "No response set"), ephemeral=True
        )

    @button(label="Guild Invite", style=ButtonStyle.grey)
    async def invite(self, interaction: Interaction, button: Button):
        """
        Create an invite link for the guild and send it as a response.
        """
        await interaction.response.send_message(
            self.response_messages.get("guild-invite", "No response set"),
            ephemeral=True,
        )


class OwnerLogs:
    """
    Log guild blacklists and unblacklists as well as user blacklists and unblacklists.
    """


# Economy thing
class devAmount(Converter):
    async def convert(self, ctx: Context, argument: str):
        argument = argument.replace(",", "").lower()
        multipliers = {
            "k": 1_000,
            "m": 1_000_000,
            "b": 1_000_000_000,
            "t": 1_000_000_000_000,
        }

        wallet_balance = (
            await ctx.bot.pool.fetchrow(
                "SELECT wallet FROM economy WHERE user_id = $1", ctx.author.id
            )
        )["wallet"]

        if argument[-1] in multipliers:
            num_part = argument[:-1]
            suffix = argument[-1]
            try:
                amount = int(float(num_part) * multipliers[suffix])
                if amount <= 0:
                    raise BadArgument("Amount must be positive!")
                return amount
            except ValueError:
                raise BadArgument("Invalid amount format!")

        try:
            amount = int(argument)
            if amount <= 0:
                raise BadArgument("Amount must be positive!")
            if amount > wallet_balance:
                raise BadArgument("You don't have enough money in your wallet!")
            return amount
        except ValueError:
            raise BadArgument("Invalid amount format!")
