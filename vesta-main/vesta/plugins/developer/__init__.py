import datetime

from discord import (
    User,
    Message,
    Embed,
    Guild,
    ButtonStyle,
)
from discord.ext.commands import Cog, command, group, parameter
from discord.ui import View, Button, button
from discord.utils import format_dt
from vesta.framework import Vesta, Context
from vesta.framework.tools.conversion import PartialAttachment
from .classes import OwnerID, devAmount


class Developer(
    Cog,
    command_attrs=dict(hidden=True),
):
    def __init__(self, bot: Vesta):
        self.bot = bot

    async def cog_check(self, ctx: Context) -> bool:  # type: ignore
        return ctx.author.id in list(self.bot.owner_ids or [])

    @group(name="vesta", invoke_without_command=True)
    async def vesta(self, ctx: Context) -> Message:
        """
        Manage bot settings.
        """
        return await ctx.send_help(ctx.command)

    @vesta.command(name="avatar", aliases=["pfp"])
    async def vesta_avatar(
        self,
        ctx: Context,
        attachment: PartialAttachment = parameter(
            default=PartialAttachment.fallback,
        ),
    ) -> Message:
        """
        Update the bot's avatar.
        """
        if not attachment.is_image():
            return await ctx.embed("The attachment must be an image!", "warned")

        await self.bot.user.edit(avatar=attachment.buffer)
        return await ctx.embed("Updated the bot's avatar!", "approved")

    @vesta.command(name="banner")
    async def vesta_banner(
        self,
        ctx: Context,
        attachment: PartialAttachment = parameter(
            default=PartialAttachment.fallback,
        ),
    ) -> Message:
        """
        Update the bot's banner.
        """
        if not attachment.is_image():
            return await ctx.embed("The attachment must be an image!", "warned")

        await self.bot.user.edit(banner=attachment.buffer)
        return await ctx.embed("Updated the bot's banner!", "approved")

    @command(aliases=["mu"])
    async def mutuals(self, ctx: Context, user: User) -> Message:
        """
        Check which mutuals a user has with Evict.
        """
        entries = sorted(
            [
                f"{guild.name} (`{guild.id}`) - **{guild.member_count}**"
                for guild in self.bot.guilds
                if user in guild.members
            ],
            key=lambda x: self.bot.get_guild(
                int(x.split("(`")[1].split("`)")[0])
            ).member_count,
            reverse=True,
        )
        if not entries:
            return await ctx.embed(
                f"`{user}` has no mutual guilds with {self.bot.user.name.capitalize()}",
                "warned",
            )

        embed = Embed(title=f"{len(entries)} Mutual Guilds with {user}")
        return await ctx.paginate(entries, embed=embed)

    @command(aliases=["g"])
    async def guilds(self, ctx: Context) -> Message:
        """
        Check which guilds Evict is in.
        """
        entries = sorted(
            [
                f"{guild.name} (`{guild.id}`) - **{guild.member_count}**"
                for guild in self.bot.guilds
            ],
            key=lambda x: self.bot.get_guild(
                int(x.split("(`")[1].split("`)")[0])
            ).member_count,
            reverse=True,
        )

        embed = Embed(title=f"{len(entries)} Guilds")
        return await ctx.paginate(entries, embed=embed)

    @group(name="guild", invoke_without_command=True)
    async def guild(self, ctx: Context) -> Message:
        """
        Blacklist, unblacklist and manage guilds.
        """
        return await ctx.send_help(ctx.command)

    @guild.command(name="blacklist")
    async def guild_blacklist(
        self, ctx: Context, guild_id: int, *, reason: str = "No reason provided"
    ) -> Message:
        """
        Blacklist and unblacklist guilds.
        """
        record = await self.bot.pool.fetchrow(
            """
            SELECT * FROM guildblacklist 
            WHERE guild_id = $1
            AND information = $2
            """,
            guild_id,
            reason,
        )

        if not record:
            guild = self.bot.get_guild(guild_id)

            if guild:
                await guild.leave()

            await self.bot.pool.execute(
                """
                INSERT INTO guildblacklist (guild_id, information)
                VALUES ($1, $2)
                """,
                guild_id,
                reason,
            )
            return await ctx.embed(f"Blacklisted guild `{guild_id}`", "approved")

        await ctx.prompt(f"Would you like to unblacklist `{guild_id}`?")
        await self.bot.pool.execute(
            """
            DELETE FROM guildblacklist
            WHERE guild_id = $1
            """,
            guild_id,
        )
        return await ctx.embed(f"Unblacklisted guild `{guild_id}`", "approved")

    @guild.command(name="leave")
    async def guild_leave(self, ctx: Context, guild_id: int) -> Message:
        """
        Leave a guild.
        """
        guild = self.bot.get_guild(guild_id)
        if not guild:
            return await ctx.embed(f"Guild ``{guild_id}`` not found!", "warned")

        await guild.leave()
        return await ctx.embed(f"Left guild `{guild_id}`", "approved")

    @guild.command(name="list")
    async def guild_list(self, ctx: Context) -> Message:
        """
        List all blacklisted guilds.
        """
        records = await self.bot.pool.fetch(
            """
            SELECT * FROM guildblacklist
            """
        )

        if not records:
            return await ctx.embed("No blacklisted guilds found!", "warned")

        entries = [
            f"**{record['guild_id']}** - {record['information']}" for record in records
        ]
        embed = Embed(title=f"{len(entries)} Blacklisted Guilds")
        return await ctx.paginate(entries, embed=embed)

    @guild.command(name="get")
    async def guild_get(self, ctx: Context, guild_id: int) -> Message:
        """
        Get a guild by ID.
        """
        guild = self.bot.get_guild(guild_id)
        if not guild:
            return await ctx.embed(f"Guild ``{guild_id}`` not found!", "warned")

        embed = Embed(
            description=f"**Created:** {format_dt(guild.created_at, style='D')} ({format_dt(guild.created_at, style='R')})"
        )
        if guild.description:
            embed.description += f"\n**Description:** {guild.description}"

        invite = guild.vanity_url_code or await guild.text_channels[0].create_invite(
            max_age=0
        )

        view = OwnerID(
            response_messages={
                "owner-id": f"{guild.owner_id}",
                "guild-invite": f"{invite}",
            }
        )

        embed.set_author(
            name=guild.name, icon_url=guild.icon.url if guild.icon else None
        )
        embed.add_field(
            name="Counts",
            value=f"Emojis: {len(guild.emojis)}\nRoles: {len(guild.roles)}\nStickers: {len(guild.stickers)}",
            inline=True,
        )
        embed.add_field(
            name="Members",
            value=f"Humans: {len([m for m in guild.members if not m.bot])}\nBots: {len([m for m in guild.members if m.bot])}\nTotal: {guild.member_count}",
            inline=True,
        )
        embed.add_field(
            name="Channels",
            value=f"Text: {len(guild.text_channels)}\nVoice: {len(guild.voice_channels)}\nCategories: {len(guild.categories)}",
            inline=True,
        )
        embed.add_field(
            name="Boost",
            value=f"Boost Level: {guild.premium_tier}\nBoost Count: {guild.premium_subscription_count}\nLevel: {guild.premium_tier}",
            inline=True,
        )
        embed.add_field(
            name="Basic Info",
            value=f"Owner: {guild.owner.name} (``{guild.owner_id}``)\nVerification Level: {guild.verification_level}\nVanity URL: {guild.vanity_url_code if guild.vanity_url_code else 'None'}",
            inline=True,
        )
        embed.set_footer(text=f"Guild ID: {guild.id}")
        return await ctx.send(embed=embed, view=view)

    @guild.command(name="portal")
    async def portal(self, ctx: Context, guild: Guild):
        """
        Create an invite to a guild.
        """
        if not guild:
            return await ctx.embed("Guild not found!", "warned")

        invite = await guild.text_channels[0].create_invite(max_age=0)

        view = View()
        view.add_item(
            Button(
                label=f"Invite to {guild.name}",
                url=str(invite),
                style=ButtonStyle.link,
            )
        )
        embed = Embed(
            description=f"The invite to ``{guild.name}`` (`{guild.id}`) is below."
        )
        return await ctx.author.send(embed=embed, view=view)

    @command()
    async def selfunban(self, ctx: Context, guild: Guild):
        """
        Have the bot unban you from the specified server.
        """
        banned = await self.bot.fetch_guild(guild.id)
        user = ctx.author

        try:
            await banned.unban(user, reason=f"{user.name} | self unban")
            await ctx.embed(
                f"You have been unbanned from ``{banned.name}``!", "approved"
            )

        except:
            await ctx.prompt(
                f"I could not unban you from ``{banned.name}``! Would you like me to leave?"
            )
            await banned.leave()
            return await ctx.embed(f"I have left ``{banned.name}``!", "approved")

    @command()
    async def upload(
        self,
        ctx: Context,
        name,
        attachment: PartialAttachment = parameter(default=PartialAttachment.fallback),
    ) -> Message:
        """
        Upload an attachment to the bot's storage.
        """
        path = f"/root/cdn/cdn_root/files/{name}"
        with open(path, "wb") as f:
            f.write(attachment.buffer)

        embed = Embed(title="File Uploaded", timestamp=datetime.datetime.now())
        embed.add_field(name="File Path", value=path)
        embed.add_field(name="File URL", value=f"https://cdn.evict.bot/files/{name}")
        return await ctx.send(embed=embed)

    @command()
    async def sync(self, ctx: Context) -> Message:
        """
        Sync all slash commands.
        """
        await self.bot.tree.sync()
        await ctx.embed("Synced all slash commands!", "approved")

    @group(name="economy", aliases=["eco"], invoke_without_command=True)
    async def economy(self, ctx: Context):
        """
        Economy management commands.
        """
        await ctx.send_help(ctx.command)

    @economy.command(name="give")
    async def economy_give(
        self, ctx: Context, user: User, amount: devAmount
    ) -> Message:
        """
        Give money to a user.
        """
        record = await self.bot.pool.fetchrow(
            """
            SELECT * FROM economy 
            WHERE user_id = $1
            """,
            user.id,
        )
        if not record:
            return await ctx.embed(
                f"**{user.name}** does not have an economy account!", "warned"
            )

        await self.bot.pool.execute(
            """
            UPDATE economy SET wallet = wallet + $1 
            WHERE user_id = $2
            """,
            amount,
            user.id,
        )

        return await ctx.embed(
            f"Successfully gave **${amount:,}** to {user.display_name}!", "approved"
        )

    @economy.command(name="remove")
    async def economy_remove(
        self, ctx: Context, user: User, amount: devAmount
    ) -> Message:
        """
        Remove money from a user.
        """
        record = await self.bot.pool.fetchrow(
            "SELECT 1 FROM economy WHERE user_id = $1", user.id
        )
        if not record:
            return await ctx.embed(
                f"**{user.name}** does not have an economy account!", "warned"
            )

        wallet_balance = await self.bot.pool.fetchval(
            "SELECT wallet FROM economy WHERE user_id = $1", user.id
        )
        if amount > wallet_balance:
            return await ctx.embed(
                f"You can't give a negative balance to **{user.display_name}**!",
                "warned",
            )

        await self.bot.pool.execute(
            "UPDATE economy SET wallet = wallet - $1 WHERE user_id = $2",
            amount,
            user.id,
        )

        return await ctx.embed(
            f"Successfully removed **${amount:,}** from {user.display_name}!",
            "approved",
        )


async def setup(bot: "Vesta") -> None:
    await bot.add_cog(Developer(bot))
