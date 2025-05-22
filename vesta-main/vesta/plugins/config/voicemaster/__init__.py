from discord import Member, VoiceChannel, CategoryChannel, VoiceState
from discord.ext.commands import Cog, command, has_permissions, cooldown, group

from vesta.framework import Vesta, Context

# def voicemaster_check():
#     """
#     Check if the user is in a voicechannel owned by the bot.
#     """
#     async def predicate(ctx: Context):
#         record = await ctx.bot.pool.fetchrow(
#             """
#             SELECT """


class VoiceMaster(Cog):
    """
    Commands for managing voice channels.
    This includes creating, deleting, and modifying voice channels.
    """

    def __init__(self, bot: Vesta):
        self.bot = bot

    @Cog.listener("on_voice_state_update")
    async def create_voice_channel(
        self, member: Member, before: VoiceState, after: VoiceState
    ):
        """
        Create a voice channel when a member joins a voice channel.
        """
        record = await self.bot.pool.fetchrow(
            """
            SELECT guild_id FROM voicemaster
            WHERE guild_id = $1
            """,
            member.guild.id,
        )
        if not record:
            return

        if not after.channel:
            return

        if before and before.channel == after.channel:
            return

        if (before is None or before.channel is None) and after.channel is not None:
            record = await self.bot.pool.fetchrow(
                """
                SELECT voice_id 
                FROM voicemaster
                WHERE guild_id = $1
                """,
                member.guild.id,
            )
            if record:
                voice_channel = await member.guild.create_voice_channel(
                    name=f"{member.name}'s Channel",
                    category=after.channel.category,
                    reason=f"VoiceMaster / {member}",
                )
                await member.move_to(voice_channel)

    @Cog.listener("on_voice_state_update")
    async def delete_voice_channel(
        self, member: Member, before: VoiceState, after: VoiceState
    ):
        """
        Delete a voice channel when a member leaves it.
        """
        record = await self.bot.pool.fetchrow(
            """
            SELECT guild_id 
            FROM voicemaster
            WHERE guild_id = $1
            """,
            member.guild.id,
        )
        if not record:
            return

        if before.channel and len(before.channel.members) == 0:
            await before.channel.delete(reason=f"VoiceMaster / {member}")

    @group(name="voicemaster", invoke_without_command=True)
    async def voicemaster(self, ctx: Context):
        """ "
        Allow your members to create automated voice channels."
        """
        return await ctx.send_help(ctx.command)

    @voicemaster.command(name="set", aliases=["setup"])
    @has_permissions(manage_guild=True)
    async def voicemaster_set(self, ctx: Context):
        """
        Create the voice channel and panel for voicemaster.
        """
        record = await self.bot.pool.fetchrow(
            """
            SELECT guild_id 
            FROM voicemaster
            WHERE guild_id = $1
            """,
            ctx.guild.id,
        )
        if record:
            return await ctx.embed(
                "VoiceMaster is already set up for this server!", "warned"
            )

        category = await ctx.guild.create_category(
            name="VoiceMaster",
            reason=f"VoiceMaster Setup / {ctx.author}",
        )

        voice = await category.create_voice_channel(
            name="Join to Create", reason=f"VoiceMaster Setup / {ctx.author}"
        )

        channel = await category.create_text_channel(
            name="interface", reason=f"VoiceMaster Setup / {ctx.author}"
        )

        await self.bot.pool.execute(
            """
            INSERT INTO voicemaster (guild_id, voice_id, text_id, category_id)
            VALUES ($1, $2, $3, $4)
            """,
            ctx.guild.id,
            voice.id,
            channel.id,
            category.id,
        )

        return await ctx.embed(
            "VoiceMaster has been set up!oh "
            "You can now use the buttons in the interface channel to create and delete your own voice channels.",
            message_type="approved",
        )

    @voicemaster.command(name="reset", aliases=["delete"])
    @has_permissions(manage_guild=True)
    async def voicemaster_reset(self, ctx: Context):
        """
        Delete the voice channel and panel for voicemaster.
        """
        record = await self.bot.pool.fetchrow(
            """
            SELECT guild_id 
            FROM voicemaster
            WHERE guild_id = $1
            """,
            ctx.guild.id,
        )
        if not record:
            return await ctx.embed(
                "VoiceMaster is not set up for this server!", "warned"
            )

        await ctx.prompt(
            "Are you sure you want to reset the VoiceMaster configuration?"
        )
        await self.bot.pool.execute(
            """
            DELETE FROM voicemaster 
            WHERE guild_id = $1
            """,
            ctx.guild.id,
        )

        return await ctx.embed(
            "Successfully reset the VoiceMaster configuration!", "approved"
        )
