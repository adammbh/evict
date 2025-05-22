from typing import Optional

from discord.ext.commands import flag, Range

from vesta.framework.discord import FlagConverter



class Flags(FlagConverter):
    """
    Class to define flags for configuring a webhook.
    """

    username: Optional[Range[str, 1, 80]] = flag(
        aliases=["name"],
        description="The name of the webhook.",
    )
    avatar_url: Optional[str] = flag(
        aliases=["avatar"],
        description="The avatar URL of the webhook.",
    )
