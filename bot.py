import logging
import re
import os
import asyncio
import nest_asyncio
import time
import random
import string
import sqlite3
from telethon import TelegramClient, events, Button
from telethon.tl.functions.messages import GetMessagesRequest
from telethon.tl.types import InputPeerChannel, InputPeerUser, InputPeerChat
from telethon.errors import (
    ChannelPrivateError, 
    FloodWaitError, 
    MessageTooLongError,
    MediaEmptyError,
    FilePartsInvalidError,
    FileReferenceExpiredError,
    UserNotParticipantError,
    ConnectionError,
    ServerError
)
from telethon.tl.functions.channels import GetParticipantRequest
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Enable logging with more detailed format
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Get API credentials from environment variables
API_ID = int(os.getenv('API_ID'))
API_HASH = os.getenv('API_HASH')
BOT_TOKEN = os.getenv('BOT_TOKEN')

# Validate required environment variables
if not all([API_ID, API_HASH, BOT_TOKEN]):
    raise ValueError("Missing required environment variables. Please set API_ID, API_HASH, and BOT_TOKEN")

def cleanup_all_sessions():
    """Delete all session files"""
    try:
        for file in os.listdir('.'):
            if file.endswith('.session'):
                try:
                    os.remove(file)
                    logger.info(f"Removed session file: {file}")
                except Exception as e:
                    logger.error(f"Error removing session file {file}: {e}")
    except Exception as e:
        logger.error(f"Error in cleanup_all_sessions: {e}")

def generate_session_name():
    """Generate a unique session name"""
    return f'bot_session_{random.randint(1000, 9999)}'

# Clean up any existing sessions before starting
cleanup_all_sessions()

# Initialize the client with a unique session name
session_name = generate_session_name()
client = TelegramClient(session_name, API_ID, API_HASH)

# Apply nest_asyncio to allow nested event loops
nest_asyncio.apply()

CHANNEL_USERNAME = 'morsh_bots'  # without @

# Store last message time for each user
last_message_time = {}
MESSAGE_COOLDOWN = 5  # seconds between messages
MAX_MESSAGES_PER_MINUTE = 10  # maximum messages per minute per user
message_count = {}  # track message count per user
MAX_CONCURRENT_USERS = 1000  # maximum number of concurrent users
active_users = set()  # track active users

# Add this at the top of the file, after the imports
COMMAND_HANDLERS = set()

async def is_user_subscribed(user_id):
    try:
        # Get the channel entity first
        channel = await client.get_entity(CHANNEL_USERNAME)
        logger.info(f"Checking subscription for user {user_id} in channel {channel.id}")
        
        # Try different methods to check subscription
        try:
            # Method 1: Using GetParticipantRequest
            participant = await client(GetParticipantRequest(
                channel=channel,
                participant=user_id
            ))
            logger.info(f"User {user_id} is subscribed (Method 1)")
            return True
        except UserNotParticipantError:
            logger.info(f"User {user_id} is not subscribed (Method 1)")
            return False
        except Exception as e:
            logger.error(f"Error in Method 1: {e}")
            
            # Method 2: Try getting channel members
            try:
                participants = await client.get_participants(channel)
                for participant in participants:
                    if participant.id == user_id:
                        logger.info(f"User {user_id} is subscribed (Method 2)")
                        return True
                logger.info(f"User {user_id} is not subscribed (Method 2)")
                return False
            except Exception as e2:
                logger.error(f"Error in Method 2: {e2}")
                return False
                
    except Exception as e:
        logger.error(f"Error checking subscription: {e}")
        return False

async def check_cooldown(user_id):
    current_time = time.time()
    
    # Initialize user's message tracking if not exists
    if user_id not in message_count:
        message_count[user_id] = {'count': 0, 'minute_start': current_time}
    
    # Reset count if a minute has passed
    if current_time - message_count[user_id]['minute_start'] >= 60:
        message_count[user_id] = {'count': 0, 'minute_start': current_time}
    
    # Check if user has exceeded message limit
    if message_count[user_id]['count'] >= MAX_MESSAGES_PER_MINUTE:
        return False
    
    # Check cooldown
    if user_id in last_message_time:
        time_diff = current_time - last_message_time[user_id]
        if time_diff < MESSAGE_COOLDOWN:
            return False
    
    # Update tracking
    last_message_time[user_id] = current_time
    message_count[user_id]['count'] += 1
    return True

async def cleanup_inactive_users():
    """Clean up inactive users periodically"""
    while True:
        current_time = time.time()
        # Remove users who haven't sent a message in the last 5 minutes
        inactive_threshold = current_time - 300  # 5 minutes
        for user_id in list(active_users):
            if user_id in last_message_time and last_message_time[user_id] < inactive_threshold:
                active_users.remove(user_id)
                if user_id in message_count:
                    del message_count[user_id]
                if user_id in last_message_time:
                    del last_message_time[user_id]
        await asyncio.sleep(60)  # Check every minute

async def cleanup_session():
    """Clean up old session files"""
    try:
        # Wait a bit before cleanup
        await asyncio.sleep(5)
        
        # Get current session file
        current_session = f"{session_name}.session"
        
        # List all session files
        for file in os.listdir('.'):
            if file.endswith('.session') and file != current_session:
                try:
                    os.remove(file)
                    logger.info(f"Removed old session file: {file}")
                except Exception as e:
                    logger.error(f"Error removing session file {file}: {e}")
    except Exception as e:
        logger.error(f"Error in cleanup_session: {e}")

@client.on(events.NewMessage(pattern='/start'))
async def start_handler(event):
    # Ignore messages from channels and groups
    if event.is_channel or event.is_group:
        return
        
    # Ignore messages from bots
    if event.sender_id and event.sender.bot:
        return
        
    # Prevent multiple handlers from responding
    if event.id in COMMAND_HANDLERS:
        return
    COMMAND_HANDLERS.add(event.id)
        
    user = await event.get_sender()
    if not await check_cooldown(user.id):
        return
    
    if not await is_user_subscribed(user.id):
        buttons = [
            [Button.url("📢 Join Channel", "https://t.me/morsh_bots")],
            [Button.inline("✅ Check Subscription", b"check_sub")]
        ]
        await event.respond(
            "🚫 To use this bot, you must subscribe to our channel first:\n"
            "👉 [Join Morsh Bots](https://t.me/morsh_bots)\n\n"
            "After joining, click the 'Check Subscription' button below to verify:",
            buttons=buttons
        )
        return
    
    await event.respond(
        f'👋 Welcome {user.first_name}!\n\n'
        '🔒 I can help you save and forward content from any Telegram channel.\n\n'
        '📥 Just send me a Telegram channel post link\n'
        'and I will fetch its content for you.\n\n'
        'Use /help to see all available commands.'
    )

@client.on(events.CallbackQuery(data=b"check_sub"))
async def check_subscription(event):
    # Ignore callbacks from channels and groups
    if event.is_channel or event.is_group:
        return
        
    user = await event.get_sender()
    if not await check_cooldown(user.id):
        return
    
    try:
        # Show checking message
        await event.answer("Checking subscription status...", alert=False)
        
        if await is_user_subscribed(user.id):
            await event.answer("✅ You are subscribed! You can now use the bot.", alert=True)
            # Update the message to show the welcome message without buttons
            await event.edit(
                f'👋 Welcome {user.first_name}!\n\n'
                '🔒 I can help you save and forward content from any Telegram channel.\n\n'
                '📥 Just send me a Telegram channel post link\n'
                'and I will fetch its content for you.\n\n'
                'Use /help to see all available commands.'
            )
        else:
            await event.answer("❌ You are not subscribed to the channel yet! Please join and try again.", alert=True)
            # Update the message to show the subscription required message with buttons
            await event.edit(
                "🚫 To use this bot, you must subscribe to our channel first:\n"
                "👉 [Join Morsh Bots](https://t.me/morsh_bots)\n\n"
                "After joining, click the 'Check Subscription' button below to verify:",
                buttons=[
                    [Button.url("📢 Join Channel", "https://t.me/morsh_bots")],
                    [Button.inline("✅ Check Subscription", b"check_sub")]
                ]
            )
    except Exception as e:
        logger.error(f"Error in check_subscription: {e}")
        await event.answer("❌ An error occurred. Please try again.", alert=True)

@client.on(events.NewMessage(pattern='/hello'))
async def hello_handler(event):
    user = await event.get_sender()
    if not await check_cooldown(user.id):
        return
    
    if not await is_user_subscribed(user.id):
        buttons = [
            [Button.url("📢 Join Channel", "https://t.me/morsh_bots")],
            [Button.inline("✅ Check Subscription", b"check_sub")]
        ]
        await event.respond(
            "🚫 To use this bot, you must subscribe to our channel first:\n"
            "👉 [Join Morsh Bots](https://t.me/morsh_bots)\n\n"
            "After joining, click the 'Check Subscription' button below to verify:",
            buttons=buttons
        )
        return
    await event.respond(
        f'👋 Hello {user.first_name}!\n\n'
        'I\'m your content saving assistant. How can I help you today?'
    )

@client.on(events.NewMessage(pattern='/help'))
async def help_handler(event):
    user = await event.get_sender()
    if not await check_cooldown(user.id):
        return
    
    if not await is_user_subscribed(user.id):
        buttons = [
            [Button.url("📢 Join Channel", "https://t.me/morsh_bots")],
            [Button.inline("✅ Check Subscription", b"check_sub")]
        ]
        await event.respond(
            "🚫 To use this bot, you must subscribe to our channel first:\n"
            "👉 [Join Morsh Bots](https://t.me/morsh_bots)\n\n"
            "After joining, click the 'Check Subscription' button below to verify:",
            buttons=buttons
        )
        return
    await event.respond(
        '🔒 Save Restricted Content Bot\n\n'
        '📥 Save and forward content from any Telegram channel\n'
        '🔓 Access restricted content easily\n'
        '📱 Works with private and public channels\n'
        '⚡ Fast and reliable content delivery\n\n'
        'Commands:\n'
        '/start - Start using the bot\n'
        '/help - Show this help message\n'
        '/hello - Get a friendly greeting\n\n'
        'How to use:\n'
        '1. Send me a Telegram channel post link\n'
        '2. I will fetch and forward the content to you\n\n'
        'Note: Some channels may have restrictions'
    )

async def get_message_content(channel_username, message_id):
    """Get message content using multiple methods."""
    try:
        # Try to get the channel entity
        logger.info(f"Attempting to get entity for channel: {channel_username}")
        channel = await client.get_entity(channel_username)
        logger.info(f"Successfully got channel entity: {channel}")
        
        # Try different methods to get the message
        try:
            # Method 1: Direct message fetch
            logger.info(f"Method 1: Attempting direct message fetch for message ID: {message_id}")
            message = await client.get_messages(channel, ids=message_id)
            if message:
                logger.info("Method 1 succeeded")
                return message
            else:
                logger.warning("Method 1 returned no message")
        except Exception as e:
            logger.error(f"Method 1 failed with error: {str(e)}")
        
        try:
            # Method 2: Using InputPeerChannel
            if hasattr(channel, 'id'):
                logger.info(f"Method 2: Attempting InputPeerChannel fetch for channel ID: {channel.id}")
                peer = InputPeerChannel(channel.id, channel.access_hash)
                message = await client.get_messages(peer, ids=message_id)
                if message:
                    logger.info("Method 2 succeeded")
                    return message
                else:
                    logger.warning("Method 2 returned no message")
        except Exception as e:
            logger.error(f"Method 2 failed with error: {str(e)}")
        
        try:
            # Method 3: Using GetMessagesRequest
            if hasattr(channel, 'id'):
                logger.info(f"Method 3: Attempting GetMessagesRequest for message ID: {message_id}")
                result = await client(GetMessagesRequest(
                    id=[message_id]
                ))
                if result and result.messages:
                    logger.info("Method 3 succeeded")
                    return result.messages[0]
                else:
                    logger.warning("Method 3 returned no message")
        except Exception as e:
            logger.error(f"Method 3 failed with error: {str(e)}")
            
    except Exception as e:
        logger.error(f"Error in get_message_content: {str(e)}")
        raise

@client.on(events.NewMessage)
async def message_handler(event):
    # Ignore messages from channels and groups
    if event.is_channel or event.is_group:
        return
        
    # Ignore messages from bots
    if event.sender_id and event.sender.bot:
        return
        
    # Ignore messages without text
    if not event.text:
        return
        
    # Ignore command messages (they are handled by their own handlers)
    if event.text.startswith('/'):
        return
        
    # Prevent multiple handlers from responding
    if event.id in COMMAND_HANDLERS:
        return
    COMMAND_HANDLERS.add(event.id)
        
    user = await event.get_sender()
    
    # Only process messages that are direct messages to the bot
    if not event.is_private:
        return
    
    # Add user to active users set
    active_users.add(user.id)
    
    # Check if we've reached the maximum number of concurrent users
    if len(active_users) > MAX_CONCURRENT_USERS:
        await event.respond(
            "⚠️ The bot is currently experiencing high traffic. Please try again in a few minutes."
        )
        return
    
    if not await check_cooldown(user.id):
        return  # Silently ignore if on cooldown
    
    if not await is_user_subscribed(user.id):
        buttons = [
            [Button.url("📢 Join Channel", "https://t.me/morsh_bots")],
            [Button.inline("✅ Check Subscription", b"check_sub")]
        ]
        await event.respond(
            "🚫 To use this bot, you must subscribe to our channel first:\n"
            "👉 [Join Morsh Bots](https://t.me/morsh_bots)\n\n"
            "After joining, click the button below to verify:",
            buttons=buttons
        )
        return
    
    # Regular expression to match Telegram channel post links
    pattern = r'https?://t\.me/([^/]+)/(\d+)'
    match = re.search(pattern, event.text)
    
    if not match:
        return  # Silently ignore non-link messages
    
    channel_username = match.group(1)
    message_id = int(match.group(2))
    
    logger.info(f"Processing link: channel={channel_username}, message_id={message_id}")
    
    try:
        # Get the message using our enhanced method
        message = await get_message_content(channel_username, message_id)
        
        if message:
            logger.info("Successfully retrieved message, attempting to send content")
            try:
                # Try to forward first
                await client.forward_messages(
                    event.chat_id,
                    message
                )
                logger.info("Message forwarded successfully")
            except Exception as forward_error:
                logger.warning(f"Forward failed, resending content instead: {str(forward_error)}")
                try:
                    # If forward fails, resend the entire message
                    await client.send_message(
                        event.chat_id,
                        message
                    )
                except Exception as e:
                    logger.error(f"Error sending message: {str(e)}")
                    await event.respond(
                        "❌ Could not send the message. Please try again later."
                    )
        else:
            logger.warning("No message content found")
            await event.respond("Message not found.")
            
    except Exception as e:
        logger.error(f"Error fetching message: {str(e)}")
        await event.respond(
            "Sorry, I couldn't fetch the message. Please try again later."
        )

async def main():
    """Start the bot with automatic reconnection."""
    logger.info("Starting the bot...")
    while True:
        try:
            # Start the cleanup task
            asyncio.create_task(cleanup_inactive_users())
            
            # Start the bot with retry mechanism
            max_retries = 3
            retry_delay = 5
            
            for attempt in range(max_retries):
                try:
                    logger.info("Attempting to start the bot...")
                    await client.start(bot_token=BOT_TOKEN)
                    logger.info("Bot started successfully!")
                    print("Bot is running...")
                    await client.run_until_disconnected()
                    break
                except sqlite3.OperationalError as e:
                    if "database is locked" in str(e):
                        if attempt < max_retries - 1:
                            logger.warning(f"Database locked, retrying in {retry_delay} seconds...")
                            await asyncio.sleep(retry_delay)
                            retry_delay *= 2  # Exponential backoff
                        else:
                            logger.error("Max retries reached, could not start bot")
                            raise
                    else:
                        raise
        except (ConnectionError, ServerError) as e:
            logger.error(f"Connection error: {e}")
            logger.info("Attempting to reconnect in 30 seconds...")
            await asyncio.sleep(30)
            continue
        except Exception as e:
            logger.error(f"Error in main: {e}")
            logger.info("Attempting to reconnect in 30 seconds...")
            await asyncio.sleep(30)
            continue
        finally:
            # Ensure the client is disconnected
            if client.is_connected():
                client.disconnect()
            # Clean up all session files
            cleanup_all_sessions()

if __name__ == '__main__':
    try:
        # Create new event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Run the main function
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        print("\nBot stopped by user")
        # Clean up sessions on keyboard interrupt
        cleanup_all_sessions()
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        # Clean up sessions on error
        cleanup_all_sessions()
    finally:
        # Close the event loop
        loop.close()
