import discord

from secrets import token_urlsafe
from typing import Optional, cast

from discord import HTTPException, Message, TextChannel, Embed
from discord.ext.commands import BucketType, cooldown, group, has_permissions, Cog
from discord.utils import get

from .classes import Flags
from vesta.framework import Vesta, Context
from vesta.framework.script import Script
from vesta.framework.tools.formatter import codeblock, vowel

class Webhook(Cog):
    """
    Forward messages through webhooks.
    """
    def __init__(self, bot: Vesta):
        self.bot = bot

    @group(
        aliases=["hook", "wh"],
        invoke_without_command=True,
    )
    @has_permissions(manage_webhooks=True)
    async def webhook(self, ctx: Context) -> Message:
        """
        Forward messages through webhooks.
        """
        return await ctx.send_help(ctx.command)

    @webhook.command(
        name="create",
        aliases=["new"],
    )
    @cooldown(6, 480, BucketType.guild)
    @has_permissions(manage_webhooks=True)
    async def webhook_create(
        self,
        ctx: Context,
        channel: Optional[TextChannel],
        *,
        name: Optional[str],
    ) -> Message:
        """
        Create a new webhook.
        """
        channel = cast(TextChannel, channel or ctx.channel)
        if not isinstance(channel, TextChannel):
            return await ctx.embed(
                "You can only create webhooks in text channels!", "warned"
            )

        webhook: Optional[discord.Webhook] = None
        webhook_id = cast(
            Optional[int],
            await self.bot.pool.fetchval(
                """
                SELECT webhook_id
                FROM webhook
                WHERE guild_id = $1
                AND channel_id = $2
                """,
                ctx.guild.id,
                channel.id,
            ),
        )
        if webhook_id:
            webhooks = await channel.webhooks()
            webhook = get(webhooks, id=webhook_id)

        identifier = token_urlsafe(6)
        webhook = webhook or await channel.create_webhook(
            name=name or f"Webhook {identifier}",
            reason=f"Webhook created by {ctx.author} ({ctx.author.id})",
        )

        await self.bot.pool.execute(
            """
            INSERT INTO webhook (
                identifier,
                guild_id,
                channel_id,
                author_id,
                webhook_id
            ) VALUES ($1, $2, $3, $4, $5)
            ON CONFLICT (channel_id, webhook_id) DO UPDATE
            SET identifier = EXCLUDED.identifier
            """,
            identifier,
            ctx.guild.id,
            channel.id,
            ctx.author.id,
            webhook.id,
        )
        return await ctx.embed(
            f"Successfully created a new **webhook** with the identifier `{identifier}`",
            "approved",
        )

    @webhook.command(name="delete", aliases=["del"], example="42345435")
    @has_permissions(manage_webhooks=True)
    async def webhook_delete(self, ctx: Context, identifier: str) -> Message:
        """
        Delete an existing webhook.
        """
        data = await self.bot.pool.fetchrow(
            """
            DELETE FROM webhook
            WHERE guild_id = $1
            AND identifier = $2
            RETURNING channel_id, webhook_id
            """,
            ctx.guild.id,
            identifier,
        )
        if not data:
            return await ctx.embed("No webhook exists with that identifier!", "warned")

        channel = cast(Optional[TextChannel], self.bot.get_channel(data["channel_id"]))
        if channel:
            webhooks = await channel.webhooks()
            webhook = get(webhooks, id=data["webhook_id"])
            if webhook:
                await webhook.delete(
                    reason=f"Webhook deleted by {ctx.author} ({ctx.author.id})"
                )

        return await ctx.embed(
            f"Successfully deleted the webhook with the identifier `{identifier}`",
            "approved",
        )

    @webhook.command(
        name="list",
        aliases=["ls"],
    )
    @has_permissions(manage_webhooks=True)
    async def webhook_list(self, ctx: Context) -> Message:
        """
        View all existing webhooks.
        """
        webhooks = [
            f"{channel.mention} - `{record['identifier']}` via {author.mention if author else '**Unknown User**'}"
            for record in await self.bot.pool.fetch(
                """
                SELECT identifier, channel_id, author_id
                FROM webhook
                WHERE guild_id = $1
                """,
                ctx.guild.id,
            )
            if (channel := ctx.guild.get_channel(record["channel_id"]))
            and (author := ctx.guild.get_member(record["author_id"]))
        ]
        if not webhooks:
            return await ctx.embed("No webhooks exist in this server!", "warned")

        return await ctx.paginate(
            entries=webhooks,
            embed=Embed(title=f"{len(webhooks)} Webhook{'s' if len(webhooks) != 1 else ''}"),
            per_page=6
        )

    @webhook.command(
        name="forward",
        aliases=["send", "fwd"],
    )
    @has_permissions(manage_webhooks=True)
    async def webhook_forward(
        self,
        ctx: Context,
        identifier: str,
        *,
        script: Script,
    ) -> Optional[Message]:
        """
        Forward a message through a webhook.
        """
        script.template, flags = await Flags().find(ctx, script.template)
        if not script:
            return await ctx.embed("You must provide a template to forward!", message_type="warned")

        data = await self.bot.pool.fetchrow(
            """
            SELECT webhook_id, channel_id
            FROM webhook
            WHERE guild_id = $1
            AND identifier = $2
            """,
            ctx.guild.id,
            identifier,
        )
        if not data:
            return await ctx.embed("No webhook exists with that identifier!", message_type="warned")

        channel = cast(Optional[TextChannel], self.bot.get_channel(data["channel_id"]))
        if not channel:
            return await ctx.embed("The channel for this webhook no longer exists!", message_type="warned")

        webhooks = await channel.webhooks()
        webhook = get(webhooks, id=data["webhook_id"])
        if not webhook:
            return await ctx.embed("The webhook for this identifier no longer exists!", message_type="warned")

        try:
            message = await script.send(
                webhook,
                wait=True,
                username=flags.username or (webhook.name or ctx.guild.name),
                avatar_url=flags.avatar_url or (webhook.avatar or ctx.guild.icon),
            )
            
        except HTTPException as exc:
            return await ctx.embed(
                "Something is wrong with your **script**!",
                codeblock(exc.text),
            )

        if channel != ctx.channel:
            return await ctx.embed(
                f"Successfully forwarded {vowel(script.format)} to {channel.mention} via **{message.author.name}**",
                message_type="approved",
            )

    @webhook.command(
        name="edit", aliases=["update"], example="3243534534 Hello, world!"
    )
    @has_permissions(manage_webhooks=True)
    async def webhook_edit(
        self,
        ctx: Context,
        message: Message,
        *,
        script: Script,
    ) -> Optional[Message]:
        """
        Edit a message sent by a webhook.
        """
        if message.guild != ctx.guild:
            return await ctx.embed(
                "The message must be in this server!",
                message_type="warned"
            )

        elif not isinstance(message.channel, TextChannel):
            return await ctx.embed(
                f"That [`message`]({message.jump_url})  was not sent in a text channel!",
                message_type="warned"
            )

        elif not message.webhook_id:
            return await ctx.embed(
                f"That [`message`]({message.jump_url}) not sent by a webhook!",
                message_type="warned"
            )

        webhooks = await message.channel.webhooks()
        webhook = get(webhooks, id=message.webhook_id)
        if not webhook:
            return await ctx.embed(
                f"The webhook for that [`message`]({message.jump_url})  no longer exists!",
                message_type="warned"
            )

        try:
            await script.edit(message, webhook=webhook)
        except HTTPException as exc:
            return await ctx.embed(
                "Something is wrong with your **script**!",
                codeblock(exc.text),
                message_type="warned"
            )

        return await ctx.embed(f"Successfully edited the [`message`({message.jump_url})]", "approved")
