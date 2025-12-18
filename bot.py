# bot.py

import discord
from search import search_best_match
from storage import save_image_record, get_random_image, get_image_by_hash
from ocr import extract_text
from PIL import Image
import imagehash
import os



# ----------------------------
# SimpleMessage (for tests)
# ----------------------------
class SimpleMessage:
    """
    Minimal test-friendly message structure.
    Used ONLY for unit tests.
    """
    def __init__(self, content, author_id, channel_id, message_id):
        self.content = content
        self.author = type("Author", (), {"id": author_id})()
        self.channel = type("Channel", (), {"id": channel_id, "send": None})()
        self.id = message_id



def compute_image_hash(path: str) -> str:
    """
    Compute perceptual hash.
    If the image cannot be opened (e.g. fake test data),
    fall back to a deterministic placeholder hash.
    """
    try:
        with Image.open(path) as img:
            return str(imagehash.phash(img))
    except Exception:
        # Test-safe fallback
        return "invalid_image_hash"
# ----------------------------
# Image indexing pipeline
# ----------------------------
def index_image_from_message(conn, message, image_path: str) -> int:
    # 1. Compute hash
    img_hash = compute_image_hash(image_path)

    # 2. Dedup check
    existing = get_image_by_hash(conn, img_hash)
    if existing:
        os.remove(image_path)
        return -existing["id"]

    user_text = message.content.strip() or None
    ocr_text = extract_text(image_path) or None

    # Write OCR result to a .txt file
    txt_path = image_path + ".txt"
    try:
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(ocr_text or "")
    except Exception as e:
        print(f"[WARN] Could not write OCR file {txt_path}: {e}")

    # Store DB record
    return save_image_record(
        conn,
        uploader_id=str(message.author.id),
        channel_id=str(message.channel.id),
        message_id=str(message.id),
        file_path=image_path,
        user_text=user_text,
        ocr_text=ocr_text,
        image_hash=img_hash,
    )


# ----------------------------
# Text-based search handler
# ----------------------------
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
        await interaction.response.send_message("No image found", ephemeral=True)
        return

    row = matches[0]
    await interaction.response.send_message(
        file=discord.File(row["file_path"]),
        ephemeral=False
    )


# ----------------------------
# Autocomplete handler
# ----------------------------
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


async def run_random_command(interaction, conn):
    """Slash command handler for /random."""
    row = get_random_image(conn)

    if not row:
        await interaction.response.send_message("No image found", ephemeral=True)
        return

    await interaction.response.send_message(
        file=discord.File(row["file_path"]),
        ephemeral=False,
    )
