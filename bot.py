# bot.py

import discord
from discord import app_commands  

from storage import save_image_record
from ocr import extract_text
from search import search_best_match

class SimpleMessage:
    """
    Tiny helper used in tests, mimicking the subset of discord.Message we need.
    """
    def __init__(self, content: str, author_id: int, channel_id: int, message_id: int):
        self.content = content
        self.author = type("Author", (), {"id": author_id})()
        self.channel = type("Channel", (), {"id": channel_id, "send": None})()
        # Note: tests replace channel with FakeChannel, so this is fine.
        self.id = message_id


def index_image_from_message(conn, message, image_path: str) -> int:
    """
    Given a message object and the downloaded image's path:
      - extract user text
      - perform OCR
      - store record in DB
    """
    user_text = message.content.strip() or None
    ocr_text = extract_text(image_path) or None

    img_id = save_image_record(
        conn,
        uploader_id=str(message.author.id),
        channel_id=str(message.channel.id),
        message_id=str(message.id),
        file_path=image_path,
        user_text=user_text,
        ocr_text=ocr_text,
    )
    return img_id


async def handle_text_query(conn, message):
    """
    Handle a text-only user message:
      - search for best image match
      - send either the image or a "not found" text message

    This function is async to match Discord's API shape.
    Tests patch `message.channel.send` to capture output.
    """
    query = message.content.strip()
    matches = search_best_match(conn, query, limit=1)

    if not matches:
        await message.channel.send("No matching image found.")
        return

    row = matches[0]
    await message.channel.send(file=discord.File(row["file_path"]))

async def run_img_command(interaction, conn, query: str):
    """
    Pure-logic function used by /img command.
    We separate this so TDD can test without real Discord client.
    """
    matches = search_best_match(conn, query, limit=1)
    if not matches:
        await interaction.response.send_message("No image found", ephemeral=True)
        return

    row = matches[0]

    # send the image
    await interaction.response.send_message(
        file=discord.File(row["file_path"]),
        ephemeral=False,
    )


async def run_img_autocomplete(interaction, conn, current: str):
    """
    Pure-logic function used by autocomplete.
    Returns at most 5 suggestions.
    """
    matches = search_best_match(conn, current, limit=5)
    choices = [
        app_commands.Choice(
            name=row["index_text"][:100],
            value=row["index_text"][:100]
        )
        for row in matches
    ]
    await interaction.response.send_autocomplete(choices)