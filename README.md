# discord-image-bot

A Test-Driven Development (TDD) Discord bot that automatically indexes uploaded images, extracts text using OCR, and performs fuzzy text search to retrieve images.  
Search works through normal text messages or through a slash command with autocomplete.

---

##  Features

###  Image Indexing
- Automatically detects image uploads
- Saves images to local storage (`data/images/`)
- Extracts text using OCR (`pytesseract`)
- Stores metadata in SQLite (`data/images.db`)
- Persists across bot restarts

###  Fuzzy Search
- Search for images using regular text messages
- `/img` slash command with autocomplete
- Supports Chinese and English fuzzy matching (RapidFuzz)
- OCR text also becomes searchable

###  Fully TDD-Based
All core modules include unit tests:
- Indexing
- Storage
- Search
- Slash commands
- Message event logic

###  Persistent Storage
Uses SQLite in WAL mode for safe concurrent writes.


### Setting
```bash
python3 -m venv venv
source venv/bin/activate   
pip install -r requirements.txt
cp .env.example .env # fix the corresponding content
# run the server
python ./main_bot.py
```

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