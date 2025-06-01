# Telegram Channel Post Fetcher Bot

This bot can fetch and forward content from Telegram channel posts, including restricted channels (when using the Telethon version).

## Setup

1. Install the required dependencies:
```bash
pip install -r requirements.txt
```

2. Create a `.env` file in the project root with the following variables:
```
# For python-telegram-bot version
TELEGRAM_BOT_TOKEN=your_bot_token_here

# For Telethon version (additional requirements)
TELEGRAM_API_ID=your_api_id_here
TELEGRAM_API_HASH=your_api_hash_here
TELEGRAM_BOT_TOKEN=your_bot_token_here
```

To get these credentials:
- Bot Token: Message [@BotFather](https://t.me/BotFather) on Telegram
- API ID and API Hash: Visit https://my.telegram.org/apps

## Usage

### Python-telegram-bot Version
Run the basic version:
```bash
python bot.py
```

### Telethon Version (for restricted channels)
Run the Telethon version:
```bash
python telethon_bot.py
```

## Features

- Fetches and forwards content from Telegram channel posts
- Works with both public and restricted channels (when using Telethon version)
- Simple command interface:
  - `/start` - Start the bot
  - `/help` - Show help message

## Notes

- The Telethon version requires you to be a member of the channel to fetch its content
- The bot will forward all types of content (text, media, files, etc.)
- Make sure you have the necessary permissions to access the channels you want to fetch from 