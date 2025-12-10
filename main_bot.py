# main_bot.py

import os
import discord
from discord import app_commands
import sqlite3

from dotenv import load_dotenv

# Import pure logic functions from bot.py (already TDD tested)
from bot import (
    index_image_from_message,
    handle_text_query,
    run_img_command,
    run_img_autocomplete,
)
from storage import init_db


# -------------------------------------------------------------
# Load environment variables
# -------------------------------------------------------------
load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = os.getenv("DISCORD_GUILD_ID")

DB_PATH = os.getenv("DB_PATH", "data/images.db")
IMAGE_FOLDER = os.getenv("IMAGE_FOLDER", "data/images")

if not TOKEN:
    raise RuntimeError("ERROR: DISCORD_TOKEN is missing in your .env file")

# Ensure folders exist
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
os.makedirs(IMAGE_FOLDER, exist_ok=True)


# -------------------------------------------------------------
# Custom Discord Client with CommandTree
# -------------------------------------------------------------
class MyBot(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True  # Required to read message content
        super().__init__(intents=intents)

        self.tree = app_commands.CommandTree(self)

        # Database connection (thread-safe)
        self.conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        self.conn.execute("PRAGMA journal_mode=WAL;")
        init_db(self.conn)

    async def setup_hook(self):
        """
        Sync slash commands when bot starts
        """
        if GUILD_ID:
            guild = discord.Object(id=int(GUILD_ID))
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
            print(f"Slash commands synced to guild {GUILD_ID}")
        else:
            await self.tree.sync()
            print("Global slash commands synced")


# Create bot instance
bot = MyBot()
tree = bot.tree


# -------------------------------------------------------------
# Slash Command: /img
# -------------------------------------------------------------
@tree.command(name="img", description="Search for an indexed image")
@app_commands.describe(query="Text used to find your image")
async def img_cmd(interaction: discord.Interaction, query: str):
    await run_img_command(interaction, bot.conn, query)


# -------------------------------------------------------------
# Autocomplete handler for /img query
# -------------------------------------------------------------
@img_cmd.autocomplete("query")
async def img_autocomplete(interaction: discord.Interaction, current: str):
    await run_img_autocomplete(interaction, bot.conn, current)


# -------------------------------------------------------------
# Message handler:
#   - If image → download & index
#   - If text → perform search
# -------------------------------------------------------------
@bot.event
async def on_message(message: discord.Message):
    # Ignore bot messages
    if message.author.bot:
        return

    # 1. Image upload → index it
    if message.attachments:
        for attachment in message.attachments:
            if attachment.content_type and "image" in attachment.content_type:

                # Ensure folder exists
                os.makedirs(IMAGE_FOLDER, exist_ok=True)

                # Unique filename (avoid duplicates)
                file_path = os.path.join(
                    IMAGE_FOLDER, f"{message.id}_{attachment.filename}"
                )

                # Save file
                await attachment.save(file_path)

                # Index into DB
                index_image_from_message(bot.conn, message, file_path)

                await message.channel.send("Image indexed!")
                return

    # 2. Text search
    text = message.content.strip()
    if text:
        await handle_text_query(bot.conn, message)


# -------------------------------------------------------------
# Run the bot
# -------------------------------------------------------------
if __name__ == "__main__":
    print("Starting Discord bot...")
    bot.run(TOKEN)
