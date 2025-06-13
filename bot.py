import asyncio
import logging
from pyrogram import Client, filters, enums
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import API_ID, API_HASH, BOT_TOKEN, BOT_USERNAME
from database import users_collection, settings_collection
from user import save_user

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='bot.log'  # Log to file for persistence
)
logger = logging.getLogger(__name__)

app = Client("my_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

async def get_user_settings(user_id):
    logger.info(f"Fetching settings for user {user_id}")
    try:
        settings = await settings_collection.find_one({"user_id": user_id})
        logger.info(f"Settings fetched for user {user_id}: {settings}")
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
        logger.info(f"Setting {key} saved for user {user_id}")
    except Exception as e:
        logger.error(f"Error saving setting {key} for user {user_id}: {e}")

@app.on_message(filters.command("start") & filters.private)
async def start_command(client, message):
    logger.info(f"Start command received from user {message.from_user.id}")
    try:
        user_id = message.from_user.id
        await save_user(user_id)
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
                "Reply with channel ID (e.g., -100123456789). Make me admin first!",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Go Back", callback_data="main_menu")]])
            )
            await callback.answer("Please reply with channel ID.")
            logger.info(f"Waiting for post channel ID from user {user_id}")

        elif data == "add_db_channel":
            settings = await get_user_settings(user_id)
            db_channels = settings.get("db_channels", [])
            if len(db_channels) >= 5:
                await callback.message.edit("Max 5 database channels allowed!")
                await callback.answer("Limit reached!")
                logger.warning(f"User {user_id} attempted to add more than 5 db channels")
                return
            await callback.message.edit(
                "Reply with channel ID (e.g., -100123456789). Make me admin first!",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Go Back", callback_data="main_menu")]])
            )
            await callback.answer("Please reply with channel ID.")
            logger.info(f"Waiting for database channel ID from user {user_id}")

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

@app.on_message(filters.text & filters.private & filters.reply)
async def handle_input(client, message):
    user_id = message.from_user.id
    logger.info(f"Received input from user {user_id}: {message.text}")
    try:
        # Check if the replied message is from the bot
        if not message.reply_to_message or message.reply_to_message.from_user.id != (await client.get_me()).id:
            logger.info(f"Ignoring non-reply input from user {user_id}")
            return

        reply_text = message.reply_to_message.text or ""
        if "Reply with channel ID" in reply_text:
            channel_id = message.text.strip()
            logger.info(f"Processing channel ID {channel_id} for user {user_id}")
            settings = await get_user_settings(user_id)
            channel_type = "post_channels" if "post channel" in reply_text.lower() else "db_channels"
            chat = await client.get_chat(channel_id)
            admins = await client.get_chat_members(channel_id, filter=enums.ChatMembersFilter.ADMINISTRATORS)
            bot_id = (await client.get_me()).id
            if not any(admin.user.id == bot_id for admin in admins):
                await message.reply("I'm not an admin in this channel!")
                logger.warning(f"Bot not admin in channel {channel_id} for user {user_id}")
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
            buttons = [
                [InlineKeyboardButton(f"Add More {channel_type.replace('_', ' ').title()}", callback_data=f"add_{channel_type}")],
                [InlineKeyboardButton("Go Back", callback_data="main_menu")]
            ]
            await message.reply("What next?", reply_markup=InlineKeyboardMarkup(buttons))

        else:
            logger.info(f"No valid input context for user {user_id}")
            await message.reply("Please select an action from the menu.")

    except Exception as e:
        logger.error(f"Error handling input for user {user_id}: {e}")
        await message.reply("Invalid input or error occurred!")
        buttons = [[InlineKeyboardButton("Go Back", callback_data="main_menu")]]
        await message.reply("What next?", reply_markup=InlineKeyboardMarkup(buttons))

if __name__ == "__main__":
    logger.info("Starting bot...")
    app.run()
    logger.info("Bot stopped.")
