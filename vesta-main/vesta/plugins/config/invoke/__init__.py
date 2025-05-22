from typing import Optional

from discord import Message
from discord.ext.commands import has_permissions, group, Cog

from vesta.framework import Vesta, Context
from vesta.framework.script import Script
from vesta.framework.tools.formatter import vowel

# This needs done redone badly. -- Sin


class Invoke(Cog):
    """
    Configure custom moderation invoke messages for actions like kick, ban, unban, timeout, and more.
    """

    def __init__(self, bot: Vesta) -> None:
        self.bot = bot

    @group(invoke_without_command=True)
    @has_permissions(manage_guild=True)
    async def invoke(self, ctx: Context) -> Message:
        """
        Set custom moderation invoke messages.
        Accepts the `moderator` and `reason` variables.
        """
        return await ctx.send_help(ctx.command)

    @invoke.group(
        name="kick",
        invoke_without_command=True,
        example="{user.mention} was kicked for {reason}",
    )
    @has_permissions(manage_guild=True)
    async def invoke_kick(self, ctx: Context, *, script: Script) -> Message:
        """
        Set the kick invoke message.
        """
        await ctx.settings.update(invoke_kick=script.template)
        return await ctx.approve(
            f"Successfully set {vowel(script.format)} **kick** message.",
            f"Use `{ctx.clean_prefix}invoke kick remove` to remove it.",
        )

    @invoke_kick.command(name="remove", aliases=["delete", "del", "rm"])
    @has_permissions(manage_guild=True)
    async def invoke_kick_remove(self, ctx: Context) -> Message:
        """
        Remove the kick invoke message.
        """
        await ctx.settings.update(invoke_kick=None)
        return await ctx.approve("Removed the **kick** invoke message!")

    @invoke.group(
        name="ban",
        invoke_without_command=True,
        example="{user.mention} was banned for {reason}",
    )
    @has_permissions(manage_guild=True)
    async def invoke_ban(self, ctx: Context, *, script: Script) -> Message:
        """
        Set the ban invoke message.
        """
        await ctx.settings.update(invoke_ban=script.template)
        return await ctx.approve(
            f"Successfully set {vowel(script.format)} **ban** message.",
            f"Use `{ctx.clean_prefix}invoke ban remove` to remove it.",
        )

    @invoke_ban.command(name="remove", aliases=["delete", "del", "rm"])
    @has_permissions(manage_guild=True)
    async def invoke_ban_remove(self, ctx: Context) -> Message:
        """
        Remove the ban invoke message.
        """
        await ctx.settings.update(invoke_ban=None)
        return await ctx.approve("Removed the **ban** invoke message!")

    @invoke.group(
        name="unban",
        invoke_without_command=True,
        example="{user.mention} was unbanned for {reason}",
    )
    @has_permissions(manage_guild=True)
    async def invoke_unban(self, ctx: Context, *, script: Script) -> Message:
        """
        Set the unban invoke message.
        """
        await ctx.settings.update(invoke_unban=script.template)
        return await ctx.approve(
            f"Successfully set {vowel(script.format)} **unban** message.",
            f"Use `{ctx.clean_prefix}invoke unban remove` to remove it.",
        )

    @invoke_unban.command(name="remove", aliases=["delete", "del", "rm"])
    @has_permissions(manage_guild=True)
    async def invoke_unban_remove(self, ctx: Context) -> Message:
        """
        Remove the unban invoke message.
        """
        await ctx.settings.update(invoke_unban=None)
        return await ctx.approve("Removed the **unban** invoke message!")

    @invoke.group(
        name="timeout",
        invoke_without_command=True,
        example="{user.mention} was timed out for {duration} ({expires})",
    )
    @has_permissions(manage_guild=True)
    async def invoke_timeout(self, ctx: Context, *, script: Script) -> Message:
        """
        Set the timeout invoke message.
        Accepts the `duration` and `expires` variables.
        """
        await ctx.settings.update(invoke_timeout=script.template)
        return await ctx.approve(
            f"Successfully set {vowel(script.format)} **timeout** message.",
            f"Use `{ctx.clean_prefix}invoke timeout remove` to remove it.",
        )

    @invoke_timeout.command(name="remove", aliases=["delete", "del", "rm"])
    @has_permissions(manage_guild=True)
    async def invoke_timeout_remove(self, ctx: Context) -> Message:
        """
        Remove the timeout invoke message.
        """
        await ctx.settings.update(invoke_timeout=None)
        return await ctx.approve("Removed the **timeout** invoke message!")

    @invoke.group(
        name="untimeout",
        invoke_without_command=True,
        example="{user.mention} was untimed out",
    )
    @has_permissions(manage_guild=True)
    async def invoke_untimeout(self, ctx: Context, *, script: Script) -> Message:
        """
        Set the untimeout invoke message.
        """
        await ctx.settings.update(invoke_untimeout=script.template)
        return await ctx.approve(
            f"Successfully set {vowel(script.format)} **untimeout** message.",
            f"Use `{ctx.clean_prefix}invoke untimeout remove` to remove it.",
        )

    @invoke_untimeout.command(
        name="remove",
        aliases=["delete", "del", "rm"],
    )
    @has_permissions(manage_guild=True)
    async def invoke_untimeout_remove(self, ctx: Context) -> Message:
        """
        Remove the untimeout invoke message.
        """
        await ctx.settings.update(invoke_untimeout=None)
        return await ctx.approve("Removed the **untimeout** invoke message!")

    @invoke.group(name="dm", invoke_without_command=True)
    @has_permissions(manage_guild=True)
    async def invoke_dm(self, ctx: Context) -> Message:
        """
        Configure DM notifications for moderation actions.
        """
        return await ctx.send_help(ctx.command)

    @invoke_dm.command(name="toggle", example="ban")
    @has_permissions(manage_guild=True)
    async def invoke_dm_toggle(self, ctx: Context, action: str) -> Message:
        """
        Toggle DM notifications for a specific action.
        Available actions: ban, unban, kick, jail, unjail, mute, unmute, warn, timeout, untimeout, antinuke_ban, antinuke_kick, antinuke_strip, antiraid_ban, antiraid_kick, antiraid_timeout, antiraid_strip, role_add, role_remove
        """
        valid_actions = [
            "ban",
            "unban",
            "kick",
            "jail",
            "unjail",
            "mute",
            "unmute",
            "warn",
            "timeout",
            "untimeout",
            "antinuke_ban",
            "antinuke_kick",
            "antinuke_strip",
            "antiraid_ban",
            "antiraid_kick",
            "antiraid_timeout",
            "antiraid_strip",
            "role_add",
            "role_remove",
        ]
        action = action.lower()
        if action not in valid_actions:
            return await ctx.warn(
                f"Invalid action. Choose from: {', '.join(f'`{a}`' for a in valid_actions)}"
            )

        try:
            exists = await self.bot.pool.fetchval(
                """
                SELECT EXISTS(SELECT 1 FROM mod WHERE guild_id = $1)
                """,
                ctx.guild.id,
            )

            if exists:
                await self.bot.pool.execute(
                    """
                    UPDATE mod 
                    SET dm_{0} = NOT COALESCE(dm_{0}, false)
                    WHERE guild_id = $1
                    """.format(action),
                    ctx.guild.id,
                )
            else:
                await self.bot.pool.execute(
                    f"""
                    INSERT INTO mod (guild_id, dm_{action}, dm_enabled) 
                    VALUES ($1, true, true)
                    """,
                    ctx.guild.id,
                )

            new_state = await self.bot.pool.fetchval(
                f"""
                SELECT dm_{action} FROM mod 
                WHERE guild_id = $1
                """,
                ctx.guild.id,
            )

            state = "enabled" if new_state else "disabled"
            return await ctx.approve(f"{state.title()} DM notifications for {action}")

        except Exception as e:
            return await ctx.error(f"Failed to toggle DM setting: {e}")

    @invoke_dm.command(name="view", example="ban")
    @has_permissions(manage_guild=True)
    async def invoke_dm_view(self, ctx: Context, action: str = None) -> Message:
        """View current DM message for an action or list all configured actions."""
        settings = await self.bot.pool.fetchrow(
            """
            SELECT * FROM mod 
            WHERE guild_id = $1
            """,
            ctx.guild.id,
        )

        if not settings:
            return await ctx.warn("No DM messages configured!")

        if not action:
            configured = []
            for col in settings.keys():
                if col.startswith("dm_") and col != "dm_enabled" and settings[col]:
                    configured.append(f"`{col[3:]}`")

            if not configured:
                return await ctx.warn("No custom DM messages configured!")
            return await ctx.approve(
                f"Configured DM messages for: {', '.join(configured)}"
            )

        action = action.lower()
        message = settings.get(f"dm_{action}")
        if not message:
            return await ctx.approve(f"Using default DM message for {action}")
        return await ctx.approve(f"Current {action} DM message:\n```\n{message}\n```")

    @invoke_dm.command(
        name="set", example="[ban] [{user.mention} was banned for {reason}]"
    )
    @has_permissions(manage_guild=True)
    async def invoke_dm_set(
        self, ctx: Context, action: str, *, script: Optional[Script] = None
    ) -> Message:
        """
        Set a custom DM message for an action.
        Available actions: ban, unban, kick, jail, unjail, mute, unmute, warn, timeout, untimeout, antinuke_ban, antinuke_kick, antinuke_strip, antiraid_ban, antiraid_kick, antiraid_timeout, antiraid_strip
        """
        valid_actions = [
            "ban",
            "unban",
            "kick",
            "jail",
            "unjail",
            "mute",
            "unmute",
            "warn",
            "timeout",
            "untimeout",
            "antinuke_ban",
            "antinuke_kick",
            "antinuke_strip",
            "antiraid_ban",
            "antiraid_kick",
            "antiraid_timeout",
            "antiraid_strip",
        ]

        action = action.lower()
        if action not in valid_actions:
            return await ctx.warn(
                f"Invalid action. Choose from: {', '.join(f'`{a}`' for a in valid_actions)}"
            )

        if not script:
            await self.bot.pool.execute(
                """
                UPDATE mod SET dm_" + action + " = NULL 
                WHERE guild_id = $1
                """,
                ctx.guild.id,
            )
            return await ctx.approve(f"Reset to default DM message for {action}")

        exists = await self.bot.pool.fetchval(
            """
            SELECT EXISTS(SELECT 1 FROM mod 
            WHERE guild_id = $1)
            """,
            ctx.guild.id,
        )

        if exists:
            await self.bot.pool.execute(
                f"""
                UPDATE mod SET dm_{action} = $1 
                WHERE guild_id = $2
                """,
                script.template,
                ctx.guild.id,
            )
        else:
            await self.bot.pool.execute(
                f"""
                INSERT INTO mod (guild_id, dm_{action}, dm_enabled) 
                VALUES ($1, $2, true)
                """,
                ctx.guild.id,
                script.template,
            )

        return await ctx.approve(f"Updated {action} DM message")
