
# discord-image-bot

A Test-Driven Development (TDD) Discord bot that automatically indexes uploaded images, extracts text using OCR, and supports fuzzy text search to retrieve images.  
Images can be searched via regular text messages or through a slash command with autocomplete.

---

## Features & Usage

### Setup and Run

> [!WARNING]
> If you would like to use CUDA for OCR, before running `pip install -r requirements.txt`, remove the `paddlepaddle` line, and see [PaddlePaddle installation docs](https://www.paddleocr.ai/latest/en/version3.x/installation.html#12-installing-paddlepaddle-via-pip) to install `paddlepaddle-gpu` on your environment.
> We have tested it on RTX 3090 with driver version: 551.76 and CUDA version: 12.4.

```bash
git clone <repo-url>
cd discord-image-bot

python3 -m venv venv
source venv/bin/activate

pip install --upgrade pip
pip install -r requirements.txt

cp .env.example .env
# Edit .env and fill in:
# DISCORD_TOKEN, DISCORD_GUILD_ID, DB_PATH, IMAGE_FOLDER

python ./main_bot.py
````

The bot will connect to Discord, initialize the database, and start listening for messages and slash commands.

---

### Image Indexing

* Automatically detects image uploads in channels
* Saves images to local storage (`data/images/`)
* Extracts text from images using OCR
* Stores metadata and extracted text in SQLite (`data/images.db`)
* Indexed data persists across bot restarts
* Sends OCR feedback to the channel after indexing

---


### Fuzzy Search

* Search indexed images using normal text messages
* `/img` slash command with autocomplete support
* Supports multi-language text recognition via OCR
* Images are searchable using both user-provided messages and OCR-extracted text
* When multiple images match, a dropdown menu allows selecting the desired image

---

### Random Selection
* `/random` slash command to get a random image uploaded previously

---

### Scheduled Messages

Independent from image indexing and search, the bot also supports scheduled messages:

* `/schedule minutes:<1-10080> content:<text> [mode:Text|Image] [channel:<#channel>]`
* `/schedule_at month:<1-12> day:<1-31> hour:<0-23> minute:<0-59> content:<text> [mode:Text|Image] [channel:<#channel>]`
  (uses the bot host’s local timezone)
* `/schedule_repeat hour:<0-23> minute:<0-59> interval:<Every minute|Every hour|Every day> content:<text> [mode:Text|Image] [channel:<#channel>]`
* `/schedule_list [limit:<1-20>]`
  Lists pending schedules in the current channel
* `/schedule_cancel schedule_id:<id>`
  Cancels schedules created by the requesting user

---

### Testing (TDD)

All core logic is covered by unit tests:

* Image indexing
* Storage and database access
* Fuzzy search
* Slash command logic
* Message event handling

Run tests with:

```bash
pytest -q
PYTHONPATH=. pytest -q   # macOS
```

---

### Persistent Storage

* Uses SQLite with WAL mode enabled
* Safe for concurrent reads and writes during bot operation

---

## Bot Setup on Discord


### Getting the Server ID (Guild ID)

1. Enable Discord Developer Mode
2. Right-click your server
3. Select **Copy Server ID**

### Creating and Configuring the Discord Bot

1. Go to [https://discord.com/developers/applications](https://discord.com/developers/applications)
2. Click **New Application**
3. Navigate to **Bot** → **Add Bot**
4. Copy the bot token and paste it into `.env`
5. Enable required intents:

   * Message Content Intent
   * Server Members Intent (optional)
   * Presence Intent (optional)
6. Save changes
7. Invite the bot to your server with permissions:

   * Send Messages
   * Read Message History
   * Use Application Commands


