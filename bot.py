import asyncio
import logging
from pyrogram import Client, filters, enums
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import PeerIdInvalid, ChatAdminRequired, MessageNotModified
from config import API_ID, API_HASH, BOT_TOKEN, BOT_USERNAME, SHORTLINK_URL, SHORTLINK_API
from database import users_collection, settings_collection, media_collection
from user import save_user

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='bot.log'
)
logger = logging.getLogger(__name__)

app = Client("my_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

async def get_user_settings(user_id):
    logger.info(f"Fetching settings for user {user_id}")
    try:
        settings = await settings_collection.find_one({"user_id": user_id})
        return settings or {}
    except Exception as e:
        logger.error(f"Error fetching settings for user {user_id}: {e}")
        return {}

async def save_user_settings(user_id, key, value):
    logger.info(f"Saving setting {key} for user {user_id}")
    try:
        await settings_collection.update_one(
            {"user_id": user_id},
            {"$set": {key: value}},
            upsert=True
        )
    except Exception as e:
        logger.error(f"Error saving setting {key} for user {user_id}: {e}")

async def validate_channel(client, channel_id, user_id, require_admin=True):
    logger.info(f"Validating channel {channel_id} for user {user_id}")
    for attempt in range(3):  # Retry 3 times
        try:
            # Attempt to send a test message first to force API sync
            try:
                await client.send_message(channel_id, f"Test message from {BOT_USERNAME} to sync interaction.")
                logger.info(f"Test message sent to channel {channel_id} on attempt {attempt + 1}")
            except ChatAdminRequired:
                if require_admin:
                    logger.warning(f"Bot lacks permission to send message in channel {channel_id}")
                    return False, "Bot needs admin permissions to send messages."
            except PeerIdInvalid:
                logger.warning(f"PEER_ID_INVALID when sending test message on attempt {attempt + 1}")
                if attempt < 2:
                    await asyncio.sleep(3)  # Wait before retry
                    continue
                return False, "Invalid channel ID or bot hasn't interacted with this channel."
            except Exception as e:
                logger.error(f"Error sending test message to channel {channel_id}: {e}")

            # Fetch chat to verify access
            chat = await client.get_chat(channel_id)
            logger.info(f"Chat fetched: {chat.title} ({chat.id})")
            bot_id = (await client.get_me()).id
            # Check bot membership
            member = await client.get_chat_member(channel_id, bot_id)
            if member.status not in [enums.ChatMemberStatus.MEMBER, enums.ChatMemberStatus.ADMINISTRATOR]:
                logger.warning(f"Bot not a member in channel {channel_id}")
                return False, "Bot is not a member of this channel."
            # Check admin status if required
            if require_admin:
                admins = []
                async for admin in client.get_chat_members(channel_id, filter=enums.ChatMembersFilter.ADMINISTRATORS):
                    admins.append(admin)
                if not any(admin.user.id == bot_id for admin in admins):
                    logger.warning(f"Bot not admin in channel {channel_id}")
                    return False, "Bot is not an admin in this channel."
            return True, ""
        except PeerIdInvalid:
            logger.error(f"PEER_ID_INVALID for channel {channel_id} on attempt {attempt + 1}")
            if attempt < 2:
                await asyncio.sleep(3)  # Wait before retry
                continue
            return False, "Invalid channel ID or bot hasn't interacted with this channel."
        except Exception as e:
            logger.error(f"Error validating channel {channel_id} on attempt {attempt + 1}: {e}")
            return False, str(e)
    return False, "Failed to validate channel after retries."

@app.on_message(filters.command("start") & filters.private)
async def start_command(client, message):
    logger.info(f"Start command received from user {message.from_user.id}")
    try:
        user_id = message.from_user.id
        await save_user(user_id)
        await save_user_settings(user_id, "input_state", None)
        welcome_msg = (
            f"Welcome to {BOT_USERNAME}! 🎉\n"
            "Store media, auto-post, search clones, and more!\n"
            "Let's get started."
        )
        buttons = [
            [InlineKeyboardButton("Let's Begin", callback_data="main_menu")]
        ]
        await message.reply(welcome_msg, reply_markup=InlineKeyboardMarkup(buttons))
        logger.info(f"Welcome message sent to user {user_id}")
    except Exception as e:
        logger.error(f"Error in start_command: {e}")
        await message.reply("Something went wrong! Try again.")

@app.on_callback_query()
async def handle_callback(client, callback):
    logger.info(f"Callback received from user {callback.from_user.id}: {callback.data}")
    try:
        user_id = callback.from_user.id
        data = callback.data

        if data == "main_menu":
            buttons = [
                [InlineKeyboardButton("Add Post Channel", callback_data="add_post_channel")],
                [InlineKeyboardButton("Add Database Channel", callback_data="add_db_channel")],
                [InlineKeyboardButton("Set Shortener", callback_data="set_shortener")],
                [InlineKeyboardButton("See Shortener", callback_data="see_shortener")],
                [InlineKeyboardButton("Set Backup Link", callback_data="set_backup_link")],
                [InlineKeyboardButton("Set FSub", callback_data="set_fsub")],
                [InlineKeyboardButton("Total Files", callback_data="total_files")],
                [InlineKeyboardButton("Clone Search Bot", callback_data="clone_search")],
                [InlineKeyboardButton("Toggle Poster", callback_data="toggle_poster")],
                [InlineKeyboardButton("Set How to Download", callback_data="set_howto")]
            ]
            await callback.message.edit(
                "Choose an option:",
                reply_markup=InlineKeyboardMarkup(buttons)
            )
            await callback.answer()
            logger.info(f"Main menu displayed for user {user_id}")

        elif data == "add_post_channel":
            settings = await get_user_settings(user_id)
            post_channels = settings.get("post_channels", [])
            if len(post_channels) >= 5:
                await callback.message.edit("Max 5 post channels allowed!")
                await callback.answer("Limit reached!")
                logger.warning(f"User {user_id} attempted to add more than 5 post channels")
                return
            new_text = (
                f"1. Add {BOT_USERNAME} to the post channel and make it an admin.\n"
                f"2. Send the channel ID (e.g., -100123456789)."
            )
            if callback.message.text != new_text:  # Prevent MESSAGE_NOT_MODIFIED
                await callback.message.edit(
                    new_text,
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Go Back", callback_data="main_menu")]])
                )
            await save_user_settings(user_id, "input_state", "add_post_channel")
            await callback.answer("Send the channel ID.")
            logger.info(f"Waiting for post channel ID from user {user_id}")

        elif data == "add_db_channel":
            settings = await get_user_settings(user_id)
            db_channels = settings.get("db_channels", [])
            if len(db_channels) >= 5:
                await callback.message.edit("Max 5 database channels allowed!")
                await callback.answer("Limit reached!")
                logger.warning(f"User {user_id} attempted to add more than 5 db channels")
                return
            new_text = (
                f"1. Add {BOT_USERNAME} to the database channel and make it an admin.\n"
                f"2. Send the channel ID (e.g., -100123456789)."
            )
            if callback.message.text != new_text:  # Prevent MESSAGE_NOT_MODIFIED
                await callback.message.edit(
                    new_text,
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Go Back", callback_data="main_menu")]])
                )
            await save_user_settings(user_id, "input_state", "add_db_channel")
            await callback.answer("Send the channel ID.")
            logger.info(f"Waiting for database channel ID from user {user_id}")

        elif data == "set_shortener":
            new_text = "Send shortener URL and API (e.g., earn4link.in your_api_key)"
            if callback.message.text != new_text:
                await callback.message.edit(
                    new_text,
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Go Back", callback_data="main_menu")]])
                )
            await save_user_settings(user_id, "input_state", "set_shortener")
            await callback.answer("Please send shortener details.")
            logger.info(f"Waiting for shortener details from user {user_id}")

        elif data == "see_shortener":
            settings = await get_user_settings(user_id)
            url = settings.get("shortlink", SHORTLINK_URL)
            api = settings.get("shortlink_api", SHORTLINK_API)
            new_text = f"Current Shortener:\nURL: {url}\nAPI: {api}"
            if callback.message.text != new_text:
                await callback.message.edit(
                    new_text,
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Go Back", callback_data="main_menu")]])
                )
            await callback.answer()
            logger.info(f"Shortener details displayed for user {user_id}")

        elif data == "set_backup_link":
            new_text = "Send the backup link URL."
            if callback.message.text != new_text:
                await callback.message.edit(
                    new_text,
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Go Back", callback_data="main_menu")]])
                )
            await save_user_settings(user_id, "input_state", "set_backup_link")
            await callback.answer("Please send backup link.")
            logger.info(f"Waiting for backup link from user {user_id}")

        elif data == "set_fsub":
            new_text = (
                f"1. Add {BOT_USERNAME} to the forced subscription channel.\n"
                f"2. Send the channel ID (e.g., -100123456789)."
            )
            if callback.message.text != new_text:
                await callback.message.edit(
                    new_text,
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Go Back", callback_data="main_menu")]])
                )
            await save_user_settings(user_id, "input_state", "set_fsub")
            await callback.answer("Send the channel ID.")
            logger.info(f"Waiting for fsub channel ID from user {user_id}")

        elif data == "total_files":
            count = await media_collection.count_documents({"user_id": user_id})
            new_text = f"You have {count} files stored."
            if callback.message.text != new_text:
                await callback.message.edit(
                    new_text,
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Go Back", callback_data="main_menu")]])
                )
            await callback.answer()
            logger.info(f"Total files displayed for user {user_id}: {count}")

        elif data == "clone_search":
            new_text = "Send search query to find files."
            if callback.message.text != new_text:
                await callback.message.edit(
                    new_text,
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Go Back", callback_data="main_menu")]])
                )
            await save_user_settings(user_id, "input_state", "clone_search")
            await callback.answer("Please send search query.")
            logger.info(f"Waiting for clone search query from user {user_id}")

        elif data == "toggle_poster":
            settings = await get_user_settings(user_id)
            current = settings.get("use_poster", True)
            await save_user_settings(user_id, "use_poster", not current)
            new_text = f"Poster is now {'ON' if not current else 'OFF'}."
            if callback.message.text != new_text:
                await callback.message.edit(
                    new_text,
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Go Back", callback_data="main_menu")]])
                )
            await callback.answer()
            logger.info(f"Poster toggled to {'ON' if not current else 'OFF'} for user {user_id}")

        elif data == "set_howto":
            new_text = "Send the 'How to Download' tutorial link."
            if callback.message.text != new_text:
                await callback.message.edit(
                    new_text,
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Go Back", callback_data="main_menu")]])
                )
            await save_user_settings(user_id, "input_state", "set_howto")
            await callback.answer("Please send howto link.")
            logger.info(f"Waiting for howto link from user {user_id}")

        else:
            logger.warning(f"Unhandled callback data: {data}")
            await callback.answer("Action not recognized!")
            buttons = [[InlineKeyboardButton("Go Back", callback_data="main_menu")]]
            await callback.message.edit(
                "Action not recognized. Please try again:",
                reply_markup=InlineKeyboardMarkup(buttons)
            )

    except MessageNotModified:
        logger.warning(f"MESSAGE_NOT_MODIFIED for user {user_id}, ignoring")
        await callback.answer()
    except Exception as e:
        logger.error(f"Error in handle_callback for user {user_id}: {e}")
        await callback.message.edit("Error occurred. Try again.")
        await callback.answer("Error occurred!")

@app.on_message(filters.text & filters.private)
async def handle_input(client, message):
    user_id = message.from_user.id
    logger.info(f"Received input from user {user_id}: {message.text}")
    try:
        settings = await get_user_settings(user_id)
        input_state = settings.get("input_state")
        if input_state not in [
            "add_post_channel", "add_db_channel", "set_shortener",
            "set_backup_link", "set_fsub", "clone_search", "set_howto"
        ]:
            logger.info(f"No input expected for user {user_id}")
            await message.reply("Please select an action from the menu.")
            return

        input_text = message.text.strip()

        if input_state in ["add_post_channel", "add_db_channel"]:
            channel_type = "post_channels" if input_state == "add_post_channel" else "db_channels"
            channel_id = input_text
            logger.info(f"Processing channel ID {channel_id} for {channel_type} by user {user_id}")
            is_valid, error_msg = await validate_channel(client, channel_id, user_id)
            if not is_valid:
                await message.reply(
                    f"Error: {error_msg}\n"
                    f"Please ensure {BOT_USERNAME} is added to the channel and made an admin.\n"
                    f"Send a message in the channel (e.g., 'Hello') and verify the channel ID (e.g., -100123456789)."
                )
                logger.error(f"Channel validation failed for {channel_id}: {error_msg}")
                return
            channels = settings.get(channel_type, [])
            if channel_id not in channels:
                channels.append(channel_id)
                await save_user_settings(user_id, channel_type, channels)
                await message.reply(f"{channel_type.replace('_', ' ').title()} connected!")
                logger.info(f"Channel {channel_id} added to {channel_type} for user {user_id}")
            else:
                await message.reply("Channel already connected!")
                logger.info(f"Channel {channel_id} already connected for user {user_id}")

        elif input_state == "set_shortener":
            try:
                url, api = input_text.split()
                await save_user_settings(user_id, "shortlink", url)
                await save_user_settings(user_id, "shortlink_api", api)
                await message.reply("Shortener set successfully!")
                logger.info(f"Shortener set for user {user_id}: {url}, {api}")
            except ValueError:
                await message.reply("Invalid format! Use: shortener_url api_key")
                logger.warning(f"Invalid shortener format from user {user_id}")
                return

        elif input_state == "set_backup_link":
            backup_link = input_text
            await save_user_settings(user_id, "backup_link", backup_link)
            await message.reply("Backup link set successfully!")
            logger.info(f"Backup link set for user {user_id}: {backup_link}")

        elif input_state == "set_fsub":
            channel_id = input_text
            logger.info(f"Processing fsub channel ID {channel_id} by user {user_id}")
            is_valid, error_msg = await validate_channel(client, channel_id, user_id, require_admin=False)
            if not is_valid:
                await message.reply(
                    f"Error: {error_msg}\n"
                    f"Please ensure {BOT_USERNAME} is added to the channel.\n"
                    f"Send a message in the channel (e.g., 'Hello') and verify the channel ID (e.g., -100123456789)."
                )
                logger.error(f"Fsub channel validation failed for {channel_id}: {error_msg}")
                return
            await save_user_settings(user_id, "fsub_channel", channel_id)
            await message.reply("Forced subscription channel set!")
            logger.info(f"Fsub set to {channel_id} for user {user_id}")

        elif input_state == "clone_search":
            query = input_text.lower()
            files = media_collection.find({"file_name": {"$regex": query, "$options": "i"}}).limit(10)
            buttons = []
            async for file in files:
                buttons.append([InlineKeyboardButton(
                    f"{file['file_name']} ({file.get('file_size', 0) / 1024 / 1024:.2f} MB)",
                    callback_data=f"clone_file_{file['file_id']}_{file['user_id']}"
                )])
            if buttons:
                await message.reply("Found files:", reply_markup=InlineKeyboardMarkup(buttons))
                logger.info(f"Search results displayed for user {user_id}")
            else:
                await message.reply("No files found.")
                logger.info(f"No search results for user {user_id}")

        elif input_state == "set_howto":
            howto_link = input_text
            await save_user_settings(user_id, "howto_link", howto_link)
            await message.reply("'How to Download' link set successfully!")
            logger.info(f"Howto link set for user {user_id}: {howto_link}")

        await save_user_settings(user_id, "input_state", None)
        buttons = [[InlineKeyboardButton("Go Back", callback_data="main_menu")]]
        await message.reply("What next?", reply_markup=InlineKeyboardMarkup(buttons))

    except Exception as e:
        logger.error(f"Error handling input for user {user_id}: {e}")
        await message.reply("An error occurred! Please try again.")
        buttons = [[InlineKeyboardButton("Go Back", callback_data="main_menu")]]
        await message.reply("What next?", reply_markup=InlineKeyboardMarkup(buttons))

if __name__ == "__main__":
    logger.info("Starting bot...")
    app.run()
    logger.info("Bot stopped.")
