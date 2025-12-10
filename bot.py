# bot.py

import discord
from search import search_best_match
from storage import save_image_record
from ocr import extract_text


def index_image_from_message(conn, message, image_path: str) -> int:
    user_text = message.content.strip() or None
    ocr_text = extract_text(image_path) or None

    return save_image_record(
        conn,
        uploader_id=str(message.author.id),
        channel_id=str(message.channel.id),
        message_id=str(message.id),
        file_path=image_path,
        user_text=user_text,
        ocr_text=ocr_text,
    )


async def handle_text_query(conn, message):
    query = message.content.strip()
    matches = search_best_match(conn, query, limit=1)

    if not matches:
        await message.channel.send("No matching image found.")
        return

    row = matches[0]
    await message.channel.send(file=discord.File(row["file_path"]))


# ----------------------------
# Slash command logic
# ----------------------------

async def run_img_command(interaction, conn, query: str):
    """Slash command handler."""
    matches = search_best_match(conn, query, limit=1)

    if not matches:
        await interaction.response.send_message("No image found.", ephemeral=True)
        return

    row = matches[0]
    await interaction.response.send_message(
        file=discord.File(row["file_path"]),
        ephemeral=False
    )


async def run_img_autocomplete(interaction, conn, current: str):
    """Autocomplete handler for /img."""
    matches = search_best_match(conn, current, limit=5)

    # Discord requires list of Choice objects
    choices = [
        discord.app_commands.Choice(
            name=(row["index_text"][:100] if row["index_text"] else "No text"),
            value=row["index_text"][:100]
        )
        for row in matches
    ]

    await interaction.response.send_autocomplete(choices)
