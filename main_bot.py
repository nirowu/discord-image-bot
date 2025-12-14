# main_bot.py
import os
import sqlite3
import discord
from discord import app_commands
from dotenv import load_dotenv

from bot import index_image_from_message
from storage import init_db, get_image_by_id
from search import search_best_match
from features.scheduling import setup_scheduling

# =========================
# Load environment
# =========================
load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = os.getenv("DISCORD_GUILD_ID")
DB_PATH = os.getenv("DB_PATH")
IMAGE_FOLDER = os.getenv("IMAGE_FOLDER")

if not TOKEN:
    raise RuntimeError("DISCORD_TOKEN missing in .env")

if not DB_PATH:
    raise RuntimeError("DB_PATH missing in .env")

if not IMAGE_FOLDER:
    raise RuntimeError("IMAGE_FOLDER missing in .env")

os.makedirs(IMAGE_FOLDER, exist_ok=True)

# =========================
# Dropdown UI
# =========================
class ImageSelect(discord.ui.Select):
    def __init__(self, matches):
        self.matches = matches

        options = [
            discord.SelectOption(
                label=row["index_text"][:50] or "(no text)",
                value=str(row["id"]),
            )
            for row in matches
        ]

        super().__init__(
            placeholder="Please choose an image:",
            min_values=1,
            max_values=1,
            options=options,
        )

    async def callback(self, interaction: discord.Interaction):
        selected_id = int(self.values[0])
        row = next(r for r in self.matches if r["id"] == selected_id)

        file_path = row["file_path"]

        if not os.path.isabs(file_path):
            file_path = os.path.join(IMAGE_FOLDER, os.path.basename(file_path))

        
        if not os.path.exists(file_path):
            await interaction.response.send_message(
                "[!] The image file does not exist.",
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            file=discord.File(file_path),
            ephemeral=False,
        )

class ImageSelectView(discord.ui.View):
    def __init__(self, matches):
        super().__init__(timeout=30)
        self.add_item(ImageSelect(matches))


# =========================
# Discord bot class
# =========================
class MyBot(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(intents=intents)

        self.tree = app_commands.CommandTree(self)

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

# =========================
# Slash command /img
# =========================
@tree.command(name="img", description="Search for an indexed image")
@app_commands.describe(query="Keyword to search image")
async def img_cmd(interaction: discord.Interaction, query: str):
    matches = search_best_match(bot.conn, query, limit=10)

    if not matches:
        await interaction.response.send_message("No image found.", ephemeral=True)
        return

    if len(matches) == 1:
        row = matches[0]
        await interaction.response.send_message(
            file=discord.File(row["file_path"]),
            ephemeral=False,
        )
        return

    view = ImageSelectView(matches)
    await interaction.response.send_message(
        f"Found {len(matches)} images, please select:",
        view=view,
        ephemeral=True,
    )


# =========================
# Message handler
# =========================
@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    # 1️⃣ Image indexing
    if message.attachments:
        for attachment in message.attachments:
            if attachment.content_type and "image" in attachment.content_type:
                file_path = os.path.join(
                    IMAGE_FOLDER, f"{message.id}_{attachment.filename}"
                )

                await attachment.save(file_path)

                img_id = index_image_from_message(bot.conn, message, file_path)
                row = get_image_by_id(bot.conn, img_id)

                ocr_text = (row.get("ocr_text") if row else None) or "(none)"
                await message.channel.send(f"Image indexed!\nOCR: {ocr_text}")
                return

    text = message.content.strip()
    if text:
        matches = search_best_match(bot.conn, text, limit=10)

        if not matches:
            await message.channel.send("No matching image found.")
            return

        if len(matches) == 1:
            await message.channel.send(
                file=discord.File(matches[0]["file_path"])
            )
            return

        view = ImageSelectView(matches)
        await message.channel.send(
            f"Found {len(matches)} images, please select:",
            view=view,
        )


# =========================
# Start bot
# =========================
if __name__ == "__main__":
    print("Starting Discord bot…")
    bot.run(TOKEN)
