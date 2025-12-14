# main_bot.py

import os
import sqlite3
import discord
from discord import app_commands
from dotenv import load_dotenv

from bot import (
    index_image_from_message,
    handle_text_query,
    run_img_command,
    run_img_autocomplete,
)
from storage import init_db
from features.scheduling import setup_scheduling


# ----------------------
# Load environment
# ----------------------
load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = os.getenv("DISCORD_GUILD_ID")
DB_PATH = os.getenv("DB_PATH", "data/images.db")
IMAGE_FOLDER = os.getenv("IMAGE_FOLDER", "data/images")

os.makedirs(IMAGE_FOLDER, exist_ok=True)

if not TOKEN:
    raise RuntimeError("DISCORD_TOKEN missing in .env")


# ----------------------
# Discord bot class
# ----------------------
class MyBot(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(intents=intents)

        self.tree = app_commands.CommandTree(self)

        # SQLite: allow cross-thread
        self.conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        self.conn.execute("PRAGMA journal_mode=WAL;")
        init_db(self.conn)

    async def setup_hook(self):
        # Register feature commands BEFORE syncing, otherwise Discord won't see them.
        setup_scheduling(self)

        if GUILD_ID:
            guild = discord.Object(id=int(GUILD_ID))
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
            print(f"Slash commands synced to guild {GUILD_ID}")
        else:
            await self.tree.sync()
            print("Global slash commands synced")


bot = MyBot()
tree = bot.tree


# ----------------------
# /img slash command
# ----------------------
@tree.command(name="img", description="Search for an indexed image")
@app_commands.describe(query="Keyword to search image")
async def img_cmd(interaction: discord.Interaction, query: str):
    await run_img_command(interaction, bot.conn, query)


@img_cmd.autocomplete("query")
async def img_autocomplete(interaction: discord.Interaction, current: str):
    return await run_img_autocomplete(interaction, bot.conn, current)

# ----------------------
# Message handler
# ----------------------
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    # 1. Image upload → index it
    if message.attachments:
        for attachment in message.attachments:
            if attachment.content_type and "image" in attachment.content_type:
                file_path = f"{IMAGE_FOLDER}/{message.id}_{attachment.filename}"
                await attachment.save(file_path)

                index_image_from_message(bot.conn, message, file_path)
                await message.channel.send("Image indexed!")
                return

    # 2. Text message → keyword search
    text = message.content.strip()
    if text:
        await handle_text_query(bot.conn, message)


# ----------------------
# Start bot
# ----------------------
if __name__ == "__main__":
    print("Starting Discord bot…")
    bot.run(TOKEN)
