import asyncio
import logging
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import API_ID, API_HASH, BOT_TOKEN, BOT_USERNAME
from database import users_collection
from user import save_user

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Client("my_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

@app.on_message(filters.command("start") & filters.private)
async def start_command(client, message):
    from channel import get_user_settings, save_user_settings
    logger.info(f"Start command received from user {message.from_user.id}")
    try:
        user_id = message.from_user.id
        await save_user(user_id)
        # Reset input state on start
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

@app.on_callback_query(filters.regex("main_menu"))
async def main_menu(client, callback):
    from channel import get_user_settings
    logger.info(f"Main menu button clicked by user {callback.from_user.id}")
    try:
        user_id = callback.from_user.id
        settings = await get_user_settings(user_id)
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
    except Exception as e:
        logger.error(f"Error in main_menu: {e}")
        await callback.message.edit("Error displaying menu. Try again.")
        await callback.answer("Error occurred!")

if __name__ == "__main__":
    logger.info("Starting bot...")
    app.run()
    logger.info("Bot stopped.")
