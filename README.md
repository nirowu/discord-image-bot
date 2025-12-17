# discord-image-bot

A Test-Driven Development (TDD) Discord bot that automatically indexes uploaded images, extracts text using OCR, and performs fuzzy text search to retrieve images.  
Search works through normal text messages or through a slash command with autocomplete.

---

##  Features

### Setting
```bash
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env # fix the corresponding content
# run the server
python ./main_bot.py
```

###  Image Indexing
- Automatically detects image uploads
- Saves images to local storage (`data/images/`)
- Extracts text using OCR (`pytesseract`)
- Stores metadata in SQLite (`data/images.db`)
- Persists across bot restarts

 ### Fuzzy Search
- Search indexed images using regular text messages
- `/img` slash command with autocomplete support
- Supports Chinese and English text recognition via OCR (EasyOCR)
- Images are searchable using both user-provided messages and OCR-extracted text

### Random Selection
- `/random` slash command to get a random image uploaded previously

### Scheduled Messages
Schedule a message to be sent later (independent from image indexing/search):
- `/schedule minutes:<1-10080> content:<text> [mode:Text|Image] [channel:<#channel>]`
- `/schedule_at month:<1-12> day:<1-31> hour:<0-23> minute:<0-59> content:<text> [mode:Text|Image] [channel:<#channel>]` (uses the bot host's local timezone)
- `/schedule_repeat hour:<0-23> minute:<0-59> interval:<Every minute|Every hour|Every day> content:<text> [mode:Text|Image] [channel:<#channel>]`
- `/schedule_list [limit:<1-20>]` (lists pending schedules in the current channel)
- `/schedule_cancel schedule_id:<id>` (only cancels schedules created by you)

###  Fully TDD-Based
All core modules include unit tests:
- Indexing
- Storage
- Search
- Slash commands
- Message event logic

```bash
pytest -q
PYTHONPATH=. pytest -q # mac
```

###  Persistent Storage
Uses SQLite in WAL mode for safe concurrent writes.


### Note
How to get server ID (guild ID)
1. Enable Discord Developer Mode
2. Right-click your server → Copy Server ID

Create & Configure Your Discord Bot
1. Go to: https://discord.com/developers/applications
2. Click New Application
3. Go to Bot → Add Bot
4. Copy the Token → paste into .env
5. Enable Intents:
    - Message Content Intent
    - Server Members Intent (optional)
    - resence Intent (optional)
6. Click Save Changes
