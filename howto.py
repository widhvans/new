from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from channel import get_user_settings, save_user_settings
from bot import app, logger

@app.on_callback_query(filters.regex("set_howto"))
async def set_howto(client, callback):
    user_id = callback.from_user.id
    logger.info(f"Set howto link initiated by user {user_id}")
    try:
        await callback.message.edit(
            "Send the 'How to Download' tutorial link.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Go Back", callback_data="main_menu")]])
        )
        await save_user_settings(user_id, "input_state", "set_howto")
        logger.info(f"Waiting for howto link from user {user_id}")
    except Exception as e:
        logger.error(f"Error in set_howto: {e}")
        await callback.message.edit("Error occurred. Try again.")

@app.on_message(filters.text & filters.private)
async def handle_howto_link(client, message):
    user_id = message.from_user.id
    logger.info(f"Received howto link input from user {user_id}: {message.text}")
    try:
        settings = await get_user_settings(user_id)
        if settings.get("input_state") != "set_howto":
            logger.info(f"No howto link input expected for user {user_id}")
            return
        howto_link = message.text.strip()
        await save_user_settings(user_id, "howto_link", howto_link)
        await save_user_settings(user_id, "input_state", None)
        await message.reply("'How to Download' link set successfully!")
        logger.info(f"Howto link set for user {user_id}: {howto_link}")
        await message.reply(
            "What next?",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Go Back", callback_data="main_menu")]])
        )
    except Exception as e:
        logger.error(f"Error handling howto link for user {user_id}: {e}")
        await message.reply("Invalid link!")
        await message.reply(
            "What next?",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Go Back", callback_data="main_menu")]])
        )
