from discord import Member, Message
from discord.ext.commands import Cog, command, BucketType, cooldown, has_permissions

from typing import Optional

from vesta.framework import Vesta, Context
from vesta.framework.discord.checks import roleplay_enabled
from .classes import NekoAPISend


class Roleplay(Cog):
    def __init__(self, bot: Vesta):
        self.bot = bot

    @command()
    @has_permissions(manage_guild=True)
    async def roleplay(self, ctx: Context, enabled: bool):
        """
        Enable or disable roleplay commands for the guild.
        """
        await self.bot.pool.execute(
            """
            INSERT INTO roleplay_enabled (guild_id, enabled)
            VALUES ($1, $2)
            ON CONFLICT (guild_id)
            DO UPDATE SET enabled = EXCLUDED.enabled
            """,
            ctx.guild.id,
            enabled,
        )
        await ctx.embed(
            f"Roleplay commands have been **{'enabled' if enabled else 'disabled'}** for this server",
            "approved",
        )

    @command()
    @cooldown(1, 1, BucketType.member)
    @roleplay_enabled()
    async def slap(self, ctx: Context, member: Optional[Member] = None) -> Message:
        """
        Slap someone.
        """
        if member is None:
            member = ctx.author
        return await NekoAPISend.send(self, ctx, member, "slap")

    @command()
    @cooldown(1, 1, BucketType.member)
    @roleplay_enabled()
    async def hug(self, ctx: Context, member: Optional[Member] = None) -> Message:
        """
        Hug someone.
        """
        if member is None:
            member = ctx.author
        return await NekoAPISend.send(self, ctx, member, "hug")

    @command()
    @cooldown(1, 1, BucketType.member)
    @roleplay_enabled()
    async def kiss(self, ctx: Context, member: Optional[Member] = None) -> Message:
        """
        Kiss someone.
        """
        if member is None:
            member = ctx.author
        return await NekoAPISend.send(self, ctx, member, "kiss")

    @command()
    @cooldown(1, 1, BucketType.member)
    @roleplay_enabled()
    async def pat(self, ctx: Context, member: Optional[Member] = None) -> Message:
        """
        Pat someone.
        """
        if member is None:
            member = ctx.author
        return await NekoAPISend.send(self, ctx, member, "pat")

    @command()
    @cooldown(1, 1, BucketType.member)
    @roleplay_enabled()
    async def tickle(self, ctx: Context, member: Optional[Member] = None) -> Message:
        """
        Tickle someone.
        """
        if member is None:
            member = ctx.author
        return await NekoAPISend.send(self, ctx, member, "tickle")

    @command()
    @cooldown(1, 1, BucketType.member)
    @roleplay_enabled()
    async def feed(self, ctx: Context, member: Optional[Member] = None) -> Message:
        """
        Feed someone.
        """
        if member is None:
            member = ctx.author
        return await NekoAPISend.send(self, ctx, member, "feed")

    @command()
    @cooldown(1, 1, BucketType.member)
    @roleplay_enabled()
    async def punch(self, ctx: Context, member: Optional[Member] = None) -> Message:
        """
        Punch someone.
        """
        if member is None:
            member = ctx.author
        return await NekoAPISend.send(self, ctx, member, "punch")

    @command()
    @cooldown(1, 1, BucketType.member)
    @roleplay_enabled()
    async def highfive(self, ctx: Context, member: Optional[Member] = None) -> Message:
        """
        Highfive someone.
        """
        if member is None:
            member = ctx.author
        return await NekoAPISend.send(self, ctx, member, "highfive")

    @command()
    @cooldown(1, 1, BucketType.member)
    @roleplay_enabled()
    async def bite(self, ctx: Context, member: Optional[Member] = None) -> Message:
        """
        Bite someone.
        """
        if member is None:
            member = ctx.author
        return await NekoAPISend.send(self, ctx, member, "bite")

    @command()
    @cooldown(1, 1, BucketType.member)
    @roleplay_enabled()
    async def bully(self, ctx: Context, member: Optional[Member] = None) -> Message:
        """
        Bully someone.
        """
        if member is None:
            member = ctx.author
        return await NekoAPISend.send(self, ctx, member, "bully")

    @command()
    @cooldown(1, 1, BucketType.member)
    @roleplay_enabled()
    async def bonk(self, ctx: Context, member: Optional[Member] = None) -> Message:
        """
        Bonk someone.
        """
        if member is None:
            member = ctx.author
        return await NekoAPISend.send(self, ctx, member, "bonk")

    @command()
    @cooldown(1, 1, BucketType.member)
    @roleplay_enabled()
    async def cringe(self, ctx: Context, member: Optional[Member] = None) -> Message:
        """
        Cringe at someone.
        """
        if member is None:
            member = ctx.author
        return await NekoAPISend.send(self, ctx, member, "cringe")

    @command()
    @cooldown(1, 1, BucketType.member)
    @roleplay_enabled()
    async def shoot(self, ctx: Context, member: Optional[Member] = None) -> Message:
        """
        Shoot someone.
        """
        if member is None:
            member = ctx.author
        return await NekoAPISend.send(self, ctx, member, "shoot")

    @command()
    @cooldown(1, 1, BucketType.member)
    @roleplay_enabled()
    async def wave(self, ctx: Context, member: Optional[Member] = None) -> Message:
        """
        Wave to someone.
        """
        if member is None:
            member = ctx.author
        return await NekoAPISend.send(self, ctx, member, "wave")

    @command()
    @cooldown(1, 1, BucketType.member)
    @roleplay_enabled()
    async def happy(self, ctx: Context, member: Optional[Member] = None) -> Message:
        """
        Be happy with someone.
        """
        if member is None:
            member = ctx.author
        return await NekoAPISend.send(self, ctx, member, "happy")

    @command()
    @cooldown(1, 1, BucketType.member)
    @roleplay_enabled()
    async def peck(self, ctx: Context, member: Optional[Member] = None) -> Message:
        """
        Peck someone.
        """
        if member is None:
            member = ctx.author
        return await NekoAPISend.send(self, ctx, member, "peck")

    @command()
    @cooldown(1, 1, BucketType.member)
    @roleplay_enabled()
    async def lurk(self, ctx: Context, member: Optional[Member] = None) -> Message:
        """
        Lurk at someone.
        """
        if member is None:
            member = ctx.author
        return await NekoAPISend.send(self, ctx, member, "lurk")

    @command()
    @cooldown(1, 1, BucketType.member)
    @roleplay_enabled()
    async def sleep(self, ctx: Context, member: Optional[Member] = None) -> Message:
        """
        Sleep with someone.
        """
        if member is None:
            member = ctx.author
        return await NekoAPISend.send(self, ctx, member, "sleep")

    @command()
    @cooldown(1, 1, BucketType.member)
    @roleplay_enabled()
    async def wink(self, ctx: Context, member: Optional[Member] = None) -> Message:
        """
        Wink at someone.
        """
        if member is None:
            member = ctx.author
        return await NekoAPISend.send(self, ctx, member, "wink")

    @command()
    @cooldown(1, 1, BucketType.member)
    @roleplay_enabled()
    async def dance(self, ctx: Context, member: Optional[Member] = None) -> Message:
        """
        Dance with someone.
        """
        if member is None:
            member = ctx.author
        return await NekoAPISend.send(self, ctx, member, "dance")

    @command()
    @cooldown(1, 1, BucketType.member)
    @roleplay_enabled()
    async def yawn(self, ctx: Context, member: Optional[Member] = None) -> Message:
        """
        Yawn at someone.
        """
        if member is None:
            member = ctx.author
        return await NekoAPISend.send(self, ctx, member, "yawn")

    @command()
    @cooldown(1, 1, BucketType.member)
    @roleplay_enabled()
    async def nom(self, ctx: Context, member: Optional[Member] = None) -> Message:
        """
        Nom someone.
        """
        if member is None:
            member = ctx.author
        return await NekoAPISend.send(self, ctx, member, "nom")

    @command()
    @cooldown(1, 1, BucketType.member)
    @roleplay_enabled()
    async def awoo(self, ctx: Context, member: Optional[Member] = None) -> Message:
        """
        Awoo at someone.
        """
        if member is None:
            member = ctx.author
        return await NekoAPISend.send(self, ctx, member, "awoo")

    @command()
    @cooldown(1, 1, BucketType.member)
    @roleplay_enabled()
    async def yeet(self, ctx: Context, member: Optional[Member] = None) -> Message:
        """
        Yeet someone.
        """
        if member is None:
            member = ctx.author
        return await NekoAPISend.send(self, ctx, member, "yeet")

    @command()
    @cooldown(1, 1, BucketType.member)
    @roleplay_enabled()
    async def think(self, ctx: Context, member: Optional[Member] = None) -> Message:
        """
        Think about someone.
        """
        if member is None:
            member = ctx.author
        return await NekoAPISend.send(self, ctx, member, "think")

    @command()
    @cooldown(1, 1, BucketType.member)
    @roleplay_enabled()
    async def bored(self, ctx: Context, member: Optional[Member] = None) -> Message:
        """
        Be bored with someone.
        """
        if member is None:
            member = ctx.author
        return await NekoAPISend.send(self, ctx, member, "bored")

    @command()
    @cooldown(1, 1, BucketType.member)
    @roleplay_enabled()
    async def blush(self, ctx: Context, member: Optional[Member] = None) -> Message:
        """
        Blush at someone.
        """
        if member is None:
            member = ctx.author
        return await NekoAPISend.send(self, ctx, member, "blush")

    @command()
    @cooldown(1, 1, BucketType.member)
    @roleplay_enabled()
    async def stare(self, ctx: Context, member: Optional[Member] = None) -> Message:
        """
        Stare at someone.
        """
        if member is None:
            member = ctx.author
        return await NekoAPISend.send(self, ctx, member, "stare")

    @command()
    @cooldown(1, 1, BucketType.member)
    async def nod(self, ctx: Context, member: Optional[Member] = None) -> Message:
        """
        Nod at someone.
        """
        if member is None:
            member = ctx.author
        return await NekoAPISend.send(self, ctx, member, "nod")

    @command()
    @cooldown(1, 1, BucketType.member)
    @roleplay_enabled()
    async def handhold(self, ctx: Context, member: Optional[Member] = None) -> Message:
        """
        Hold hands with someone.
        """
        if member is None:
            member = ctx.author
        return await NekoAPISend.send(self, ctx, member, "handhold")

    @command()
    @cooldown(1, 1, BucketType.member)
    @roleplay_enabled()
    async def smug(self, ctx: Context, member: Optional[Member] = None) -> Message:
        """
        Smug at someone.
        """
        if member is None:
            member = ctx.author
        return await NekoAPISend.send(self, ctx, member, "smug")

    @command()
    @cooldown(1, 1, BucketType.member)
    @roleplay_enabled()
    async def blush(self, ctx: Context, member: Optional[Member] = None) -> Message:
        """
        Blush at someone.
        """
        if member is None:
            member = ctx.author
        return await NekoAPISend.send(self, ctx, member, "blush")

    @command()
    @cooldown(1, 1, BucketType.member)
    @roleplay_enabled()
    async def fuck(self, ctx: Context, member: Optional[Member] = None) -> Message:
        """
        Fuck someone.
        """
        if member is None:
            member = ctx.author
        return await NekoAPISend.r2_send(self, ctx, member, "fuck")

    @command()
    @cooldown(1, 1, BucketType.member)
    @roleplay_enabled()
    async def spank(self, ctx: Context, member: Optional[Member] = None) -> Message:
        """
        Spank someone.
        """
        if member is None:
            member = ctx.author
        return await NekoAPISend.r2_send(self, ctx, member, "spank")

    @command()
    @cooldown(1, 1, BucketType.member)
    @roleplay_enabled()
    async def nutkick(self, ctx: Context, member: Optional[Member] = None) -> Message:
        """
        Nutkick someone.
        """
        if member is None:
            member = ctx.author
        return await NekoAPISend.r2_send(self, ctx, member, "nutkick")


async def setup(bot: "Vesta") -> None:
    await bot.add_cog(Roleplay(bot))
