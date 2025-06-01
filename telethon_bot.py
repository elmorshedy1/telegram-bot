import logging
import re
import os
from telethon import TelegramClient, events
from telethon.tl.functions.messages import GetMessagesRequest
from telethon.tl.types import InputPeerChannel
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Get API credentials from environment variables
API_ID = os.getenv('TELEGRAM_API_ID')
API_HASH = os.getenv('TELEGRAM_API_HASH')
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

# Initialize the client
client = TelegramClient('bot_session', API_ID, API_HASH)

@client.on(events.NewMessage(pattern='/start'))
async def start_handler(event):
    """Handle the /start command."""
    await event.respond(
        'Hi! Send me a Telegram channel post link\n'
        'and I will try to fetch its content for you.'
    )

@client.on(events.NewMessage(pattern='/help'))
async def help_handler(event):
    """Handle the /help command."""
    await event.respond(
        'To use this bot:\n'
        '1. Send me a Telegram channel post link\n'
        '2. I will try to fetch and forward the content to you\n'
        'Note: For restricted channels, you need to be a member of the channel.'
    )

@client.on(events.NewMessage)
async def message_handler(event):
    """Handle incoming messages and process Telegram links."""
    message_text = event.text
    
    # Regular expression to match Telegram channel post links
    pattern = r'https?://t\.me/([^/]+)/(\d+)'
    match = re.search(pattern, message_text)
    
    if match:
        channel_username = match.group(1)
        message_id = int(match.group(2))
        
        try:
            # Get the channel entity
            channel = await client.get_entity(channel_username)
            
            # Get the message
            message = await client.get_messages(channel, ids=message_id)
            
            if message:
                # Forward the message
                await client.forward_messages(
                    event.chat_id,
                    message
                )
            else:
                await event.respond("Message not found.")
                
        except Exception as e:
            logger.error(f"Error fetching message: {e}")
            await event.respond(
                "Sorry, I couldn't fetch the message. This might be because:\n"
                "1. The channel is private/restricted\n"
                "2. You don't have access to the channel\n"
                "3. The message doesn't exist"
            )
    elif not message_text.startswith('/'):
        await event.respond(
            "Please send a valid Telegram channel post link"
        )

async def main():
    """Start the bot."""
    # Start the client
    await client.start(bot_token=BOT_TOKEN)
    print("Bot is running...")
    await client.run_until_disconnected()

if __name__ == '__main__':
    import asyncio
    asyncio.run(main()) 