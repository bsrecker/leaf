from bot import LeafBot
from utils import Paginator
from discord.ext import commands
from discord import app_commands
import discord

from typing import Optional


@app_commands.guild_only()
class TagsCog(commands.GroupCog, name="Tags", group_name="tags"):
    def __init__(self, bot: LeafBot) -> None:
        self.bot = bot

    @app_commands.describe(starting_page="The page to start on.")
    @app_commands.command(name="list", description="Lists all the tags in the server.")
    async def list_tags(
        self,
        interaction: discord.Interaction,
        starting_page: Optional[int] = 1,
        silent: Optional[bool] = False,
    ):
        tags = await self.bot.database.fetch(
            "SELECT * FROM tags WHERE guild_id = $1 AND deleted = FALSE",
            interaction.guild.id,
        )
        embeds = []

        if not tags:
            # TODO: Remove pagination buttons if there are no tags in the server.
            embeds.append(
                discord.Embed(
                    description="There are no tags in this server.",
                    color=discord.Color.dark_embed(),
                )
            )
        else:
            chunks = list(discord.utils.as_chunks(tags, 15))
            for index, chunk in enumerate(chunks):
                embed = discord.Embed(
                    description="\n".join(
                        [f"• **{tag['name']}** (Uses: {tag['uses']})" for tag in chunk]
                    ),
                    color=discord.Color.dark_embed(),
                )
                embed.set_footer(text=f"Page {index + 1} / {len(chunks)}")
                embeds.append(embed)

        if not 0 <= (starting_page - 1) <= len(embeds):
            await interaction.response.send_message(
                embed=discord.Embed(
                    description="That page does not exist.",
                    color=discord.Color.dark_embed(),
                ),
                ephemeral=True,
            )
            return

        paginator = Paginator(embeds=embeds, index=starting_page - 1)
        await paginator.start(interaction, ephemeral=silent)

    @app_commands.describe(tag="The name of the tag to view.")
    @app_commands.command(name="view", description="Sends the content of a tag.")
    async def view_tag(
        self, interaction: discord.Interaction, tag: str, silent: Optional[bool] = False
    ) -> None:
        tag_record = await self.bot.database.fetchrow(
            "SELECT * FROM tags WHERE name = $1 AND guild_id = $2 AND deleted = FALSE",
            tag,
            interaction.guild.id,
        )

        if tag_record:
            await interaction.response.send_message(
                embed=discord.Embed(
                    title=tag_record["name"],
                    description=tag_record["content"],
                    color=discord.Color.dark_embed(),
                ),
                ephemeral=silent,
            )
        else:
            await interaction.response.send_message(
                embed=discord.Embed(
                    description="That tag does not exist.",
                    color=discord.Color.dark_embed(),
                ),
                ephemeral=silent,
            )

    @app_commands.describe(name="The tag of the newly created tag.")
    @app_commands.command(name="create", description="Creates a new tag.")
    async def create_tag(self, interaction: discord.Interaction, name: str):
        tag_record = await self.bot.database.fetchrow(
            "SELECT * FROM tags WHERE name = $1 AND guild_id = $2",
            name,
            interaction.guild.id,
        )

        if not tag_record:
            await interaction.response.send_message(
                embed=discord.Embed(
                    description="Please reply to this message with your tag content within 5 minutes.",
                    color=discord.Color.dark_embed(),
                )
            )
            message = await interaction.original_response()

            def check(message):
                return (
                    message.channel == interaction.channel
                    and message.author == interaction.user
                )

            message = await self.bot.wait_for("message", timeout=300, check=check)

            await self.bot.database.execute(
                """
                INSERT INTO tags(name, guild_id, owner_id, content, created_at, last_edited_at, uses)
                VALUES ($1, $2, $3, $4, DEFAULT, DEFAULT, DEFAULT);
                """,
                name,
                interaction.guild.id,
                interaction.user.id,
                message.content,
            )
            await message.reply(
                embed=discord.Embed(
                    description="Your tag has successfully been created.",
                    color=discord.Color.dark_embed(),
                )
            )
        else:
            await interaction.response.send_message(
                embed=discord.Embed(
                    description="That tag already exists.",
                    color=discord.Color.dark_embed(),
                )
            )

    @app_commands.describe(tag="The name of the tag to edit.")
    @app_commands.command(name="edit", description="Edits the content of a tag.")
    async def edit_tag(
        self, interaction: discord.Interaction, tag: str, silent: Optional[bool] = False
    ):
        tag_record = await self.bot.database.fetchrow(
            "SELECT * FROM Tags WHERE name = $1 AND guild_id = $2;",
            tag,
            interaction.guild.id,
        )

        if not tag_record:
            await interaction.response.send_message(
                embed=discord.Embed(
                    description="That tag does not exist.",
                    color=discord.Color.dark_embed(),
                ),
                ephemeral=silent,
            )
            return

        if (
            tag_record["owner_id"] == interaction.user.id
            or interaction.user.guild_permissions.manage_guild
        ):
            await interaction.response.send_message(
                embed=discord.Embed(
                    description="Please reply to this message with your new tag content within 5 minutes.",
                    color=discord.Color.dark_embed(),
                )
            )
            message = await interaction.original_response()

            def check(message):
                return (
                    message.channel == interaction.channel
                    and message.author == interaction.user
                )

            message = await self.bot.wait_for("message", timeout=300, check=check)
            await self.bot.database.execute(
                "UPDATE tags SET content = $1 WHERE name = $2 and guild_id = $3;",
                message.content,
                tag,
                interaction.guild.id,
            )

            await message.reply(
                embed=discord.Embed(
                    description="Your tag has successfully been edited.",
                    color=discord.Color.dark_embed(),
                )
            )
        else:
            await interaction.response.send_message(
                embed=discord.Embed(
                    description="You do not have permission to edit that tag.",
                    color=discord.Color.dark_embed(),
                ),
                ephemeral=silent,
            )

    @app_commands.describe(tag="The name of the tag to delete.")
    @app_commands.command(name="delete", description="Deletes a tag from the server.")
    async def delete_tag(
        self, interaction: discord.Interaction, tag: str, silent: Optional[bool] = False
    ) -> None:
        tag_record = await self.bot.database.fetchrow(
            "SELECT * FROM Tags WHERE name = $1 AND guild_id = $2;",
            tag,
            interaction.guild.id,
        )

        if not tag_record:
            await interaction.response.send_message(
                embed=discord.Embed(
                    description="That tag does not exist.",
                    color=discord.Color.dark_embed(),
                ),
                ephemeral=silent,
            )
            return

        if (
            tag_record["owner_id"] == interaction.user.id
            or interaction.user.guild_permissions.manage_guild
        ):
            await self.bot.database.execute(
                "UPDATE Tags SET deleted = true WHERE name = $1;", tag
            )
            await interaction.response.send_message(
                embed=discord.Embed(
                    description="The tag has successfully been deleted.",
                    color=discord.Color.dark_embed(),
                ),
                ephemeral=silent,
            )
        else:
            await interaction.response.send_message(
                embed=discord.Embed(
                    description="You do not have permission to delete that tag.",
                    color=discord.Color.dark_embed(),
                ),
                ephemeral=silent,
            )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(TagsCog(bot))
