from discord import Embed
from discord.ext.commands import (
    Cog, 
    group, 
    has_permissions
)

from vesta.framework import Context, Vesta
from vesta.framework.script import Script


class Tags(Cog):
    """
    Commands for managing tags.
    Tags are custom commands that can return predefined text or responses.
    """
    def __init__(self, bot: Vesta):
        self.bot = bot

    @group(name="tag", invoke_without_command=True)
    async def tag(self, ctx: Context, *, name: str):
        """
        Create and manage custom tags.
        If no subcommand is given, searches for and displays the requested tag.
        """
        record = await self.bot.pool.fetchrow(
            """
            SELECT original 
            FROM tag_aliases
            WHERE guild_id = $1 AND LOWER(alias) = LOWER($2)
            """,
            ctx.guild.id,
            name,
        )
        if record:
            name = record["original"]

        record = await self.bot.pool.fetchrow(
            """
            SELECT template, owner_id 
            FROM tags
            WHERE guild_id = $1 AND LOWER(name) = LOWER($2)
            """,
            ctx.guild.id,
            name,
        )

        if not record:
            return await ctx.embed(f"Tag ``{name}`` not found!", "warned")

        try:
            script = Script(record["template"], [ctx.guild, ctx.channel, ctx.author])
            await script.send(ctx)

        except Exception as e:
            return await ctx.embed(
                f"There is something wrong with your script!\n Error: {e}", "warned"
            )

    @tag.command(name="create")
    @has_permissions(manage_messages=True)
    async def tag_create(self, ctx: Context, name: str, *, script: str):
        """
        Create a new tag with the given name and template.
        """
        record = await self.bot.pool.fetchrow(
            """
            SELECT * 
            FROM tags 
            WHERE guild_id = $1 AND LOWER(name) = LOWER($2)
            """,
            ctx.guild.id,
            name,
        )
        if record:
            return await ctx.embed(f"Tag ``{name}`` already exists!", "warned")

        await self.bot.pool.execute(
            """
            INSERT INTO tags (guild_id, name, template, owner_id)
            VALUES ($1, $2, $3, $4)
            """,
            ctx.guild.id,
            name,
            script,
            ctx.author.id,
        )
        return await ctx.embed(f"Tag ``{name}`` created!", "approved")

    @tag.command(name="delete")
    @has_permissions(manage_messages=True)
    async def tag_delete(self, ctx: Context, *, name: str):
        """
        Delete an existing tag by its name.
        """
        record = await self.bot.pool.fetchrow(
            """
            SELECT * 
            FROM tags 
            WHERE guild_id = $1 AND LOWER(name) = LOWER($2)
            """,
            ctx.guild.id,
            name,
        )
        if not record:
            return await ctx.embed(f"Tag ``{name}`` not found!", "warned")

        await self.bot.pool.execute(
            """
            DELETE FROM tags 
            WHERE guild_id = $1 AND LOWER(name) = LOWER($2)
            """,
            ctx.guild.id,
            name,
        )
        return await ctx.embed(f"Tag ``{name}`` deleted!", "approved")

    @tag.command(name="edit")
    @has_permissions(manage_messages=True)
    async def tag_edit(self, ctx: Context, name: str, *, template: Script):
        """
        Edit an existing tag's template.
        """
        record = await self.bot.pool.fetchrow(
            """
            SELECT * 
            FROM tags 
            WHERE guild_id = $1 AND LOWER(name) = LOWER($2)
            """,
            ctx.guild.id,
            name,
        )
        if not record:
            return await ctx.embed(f"Tag ``{name}`` not found!", "warned")

        await self.bot.pool.execute(
            """
            UPDATE tags 
            SET template = $1 
            WHERE guild_id = $2 AND LOWER(name) = LOWER($3)
            """,
            template,
            ctx.guild.id,
            name,
        )
        return await ctx.embed(f"Tag ``{name}`` updated!", "approved")

    @tag.command(name="alias")
    @has_permissions(manage_messages=True)
    async def tag_alias(self, ctx: Context, name: str, *, alias: str):
        """
        Create an alias for an existing tag.
        """
        record = await self.bot.pool.fetchrow(
            """
            SELECT * 
            FROM tags 
            WHERE guild_id = $1 AND LOWER(name) = LOWER($2)
            """,
            ctx.guild.id,
            name,
        )
        if not record:
            return await ctx.embed(f"Tag ``{name}`` not found!", "warned")

        await self.bot.pool.execute(
            """
            INSERT INTO tag_aliases (guild_id, alias, original)
            VALUES ($1, $2, $3)
            """,
            ctx.guild.id,
            alias,
            name,
        )
        return await ctx.embed(
            f"Alias ``{alias}`` created for tag ``{name}``!", "approved"
        )

    @tag.command(name="list")
    async def tag_list(self, ctx: Context):
        """
        List all tags available in the current guild.
        """
        records = await self.bot.pool.fetch(
            """
            SELECT name 
            FROM tags 
            WHERE guild_id = $1
            """,
            ctx.guild.id,
        )
        if not records:
            return await ctx.embed("No tags found in this guild!", "warned")

        embed = Embed(title=f"{len(records)} Tag{'s' if len(records) != 1 else ''}")
        entries = [f"``{record['name']}``" for record in records]

        return await ctx.paginate(embed=embed, entries=entries)
