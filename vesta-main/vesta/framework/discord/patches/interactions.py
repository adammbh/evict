from contextlib import suppress
from typing import Literal

from discord import (
    Embed,
    InteractionResponded,
    WebhookMessage,
    Interaction,
)

from vesta.framework import Vesta

MESSAGE_TYPES = Literal["approved", "warned", "denied", "neutral"]


async def embed(self: "Vesta", message: str, **kwargs) -> WebhookMessage:
    embed = Embed(description=f"{self.user.mention}: {message}")

    with suppress(InteractionResponded):
        await self.response.defer(ephemeral=True)

    return await self.followup.send(embed=embed, ephemeral=True, **kwargs)


Interaction.embed = embed
