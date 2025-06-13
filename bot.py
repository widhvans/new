import asyncio
import logging
from pyrogram import Client, filters, enums
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import PeerIdInvalid
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

async def validate_channel(client, channel_id, user_id):
    logger.info(f"Validating channel {channel_id} for user {user_id}")
    try:
        # Resolve peer to ensure channel is accessible
        await client.resolve_peer(channel_id)
        chat = await client.get_chat(channel_id)
        logger.info(f"Chat fetched: {chat.title} ({chat.id})")
        # Check bot membership
        bot_id = (await client.get_me()).id
        try:
            member = await client.get_chat_member(channel_id, bot_id)
            if member.status not in [enums.ChatMemberStatus.MEMBER, enums.ChatMemberStatus.ADMINISTRATOR]:
                logger.warning(f"Bot not a member in channel {channel_id}")
                return False, "Bot is not a member of this channel."
        except Exception:
            logger.warning(f"Bot cannot access channel {channel_id}")
            return False, "Bot cannot access this channel."
        # Check admin status
        admins = await client.get_chat_members(channel_id, filter=enums.ChatMembersFilter.ADMINISTRATORS)
        if not any(admin.user.id == bot_id for admin in admins):
            logger.warning(f"Bot not admin in channel {channel_id}")
            return False, "Bot is not an admin in this channel."
        return True, ""
    except PeerIdInvalid:
        logger.error(f"PEER_ID_INVALID for channel {channel_id}")
        return False, "Invalid channel ID or bot hasn't interacted with this channel."
    except Exception as e:
        logger.error(f"Error validating channel {channel_id}: {e}")
        return False, str(e)

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
            await callback.message.edit(
                f"1. Add me to the post channel and make me an admin.\n"
                f"2. Send the channel's invite link (e.g., t.me/+abc123 or @ChannelName) or channel ID (e.g., -100123456789).",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Go Back", callback_data="main_menu")]])
            )
            await save_user_settings(user_id, "input_state", "add_post_channel")
            await callback.answer("Send the invite link or channel ID.")
            logger.info(f"Waiting for post channel input from user {user_id}")

        elif data == "add_db_channel":
            settings = await get_user_settings(user_id)
            db_channels = settings.get("db_channels", [])
            if len(db_channels) >= 5:
                await callback.message.edit("Max 5 database channels allowed!")
                await callback.answer("Limit reached!")
                logger.warning(f"User {user_id} attempted to add more than 5 db channels")
                return
            await callback.message.edit(
                f"1. Add me to the database channel and make me an admin.\n"
                f"2. Send the channel's invite link (e.g., t.me/+abc123 or @ChannelName) or channel ID (e.g., -100123456789).",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Go Back", callback_data="main_menu")]])
            )
            await save_user_settings(user_id, "input_state", "add_db_channel")
            await callback.answer("Send the invite link or channel ID.")
            logger.info(f"Waiting for database channel input from user {user_id}")

        elif data == "set_shortener":
            await callback.message.edit(
                "Send shortener URL and API (e.g., earn4link.in your_api_key)",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Go Back", callback_data="main_menu")]])
            )
            await save_user_settings(user_id, "input_state", "set_shortener")
            await callback.answer("Please send shortener details.")
            logger.info(f"Waiting for shortener details from user {user_id}")

        elif data == "see_shortener":
            settings = await get_user_settings(user_id)
            url = settings.get("shortlink", SHORTLINK_URL)
            api = settings.get("shortlink_api", SHORTLINK_API)
            await callback.message.edit(
                f"Current Shortener:\nURL: {url}\nAPI: {api}",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Go Back", callback_data="main_menu")]])
            )
            await callback.answer()
            logger.info(f"Shortener details displayed for user {user_id}")

        elif data == "set_backup_link":
            await callback.message.edit(
                "Send the backup link URL.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Go Back", callback_data="main_menu")]])
            )
            await save_user_settings(user_id, "input_state", "set_backup_link")
            await callback.answer("Please send backup link.")
            logger.info(f"Waiting for backup link from user {user_id}")

        elif data == "set_fsub":
            await callback.message.edit(
                f"1. Add me to the forced subscription channel.\n"
                f"2. Send the channel's invite link (e.g., t.me/+abc123 or @ChannelName) or channel ID (e.g., -100123456789).",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Go Back", callback_data="main_menu")]])
            )
            await save_user_settings(user_id, "input_state", "set_fsub")
            await callback.answer("Send the invite link or channel ID.")
            logger.info(f"Waiting for fsub channel input from user {user_id}")

        elif data == "total_files":
            count = await media_collection.count_documents({"user_id": user_id})
            await callback.message.edit(
                f"You have {count} files stored.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Go Back", callback_data="main_menu")]])
            )
            await callback.answer()
            logger.info(f"Total files displayed for user {user_id}: {count}")

        elif data == "clone_search":
            await callback.message.edit(
                "Send search query to find files.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Go Back", callback_data="main_menu")]])
            )
            await save_user_settings(user_id, "input_state", "clone_search")
            await callback.answer("Please send search query.")
            logger.info(f"Waiting for clone search query from user {user_id}")

        elif data == "toggle_poster":
            settings = await get_user_settings(user_id)
            current = settings.get("use_poster", True)
            await save_user_settings(user_id, "use_poster", not current)
            await callback.message.edit(
                f"Poster is now {'ON' if not current else 'OFF'}.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Go Back", callback_data="main_menu")]])
            )
            await callback.answer()
            logger.info(f"Poster toggled to {'ON' if not current else 'OFF'} for user {user_id}")

        elif data == "set_howto":
            await callback.message.edit(
                "Send the 'How to Download' tutorial link.",
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
            channel_id = None
            if input_text.startswith("t.me/") or input_text.startswith("@"):
                logger.info(f"Processing invite link {input_text} for {channel_type} by user {user_id}")
                try:
                    chat = await client.join_chat(input_text)
                    channel_id = str(chat.id)
                    logger.info(f"Joined channel: {chat.title} ({channel_id})")
                except Exception as e:
                    await message.reply(
                        "Invalid invite link or I couldn't join the channel. Ensure the link is correct and I'm not banned!"
                    )
                    logger.error(f"Error processing invite link {input_text} for user {user_id}: {e}")
                    return
            else:
                channel_id = input_text
                logger.info(f"Processing channel ID {channel_id} for {channel_type} by user {user_id}")

            is_valid, error_msg = await validate_channel(client, channel_id, user_id)
            if not is_valid:
                await message.reply(
                    f"Error: {error_msg}\nPlease ensure I'm added to the channel, made an admin, and send a valid invite link or ID."
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
            channel_id = None
            if input_text.startswith("t.me/") or input_text.startswith("@"):
                logger.info(f"Processing fsub invite link {input_text} by user {user_id}")
                try:
                    chat = await client.join_chat(input_text)
                    channel_id = str(chat.id)
                    logger.info(f"Joined fsub channel: {chat.title} ({channel_id})")
                except Exception as e:
                    await message.reply(
                        "Invalid invite link or I couldn't join the channel. Ensure the link is correct and I'm not banned!"
                    )
                    logger.error(f"Error processing fsub invite link {input_text} for user {user_id}: {e}")
                    return
            else:
                channel_id = input_text
                logger.info(f"Processing fsub channel ID {channel_id} by user {user_id}")

            is_valid, error_msg = await validate_channel(client, channel_id, user_id)
            if not is_valid:
                await message.reply(
                    f"Error: {error_msg}\nPlease ensure I'm added to the channel and send a valid invite link or ID."
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
