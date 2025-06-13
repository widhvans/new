from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from channel import get_user_settings, save_user_settings
from bot import app, logger

@app.on_callback_query(filters.regex("set_backup_link"))
async def set_backup_link(client, callback):
    user_id = callback.from_user.id
    await callback.message.edit(
        "Send the backup link URL.",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Go Back", callback_data="main_menu")]])
    )
    app.add_handler(
        filters.text & filters.user(user_id) & filters.private,
        lambda c, m: handle_backup_link(c, m, user_id)
    )

async def handle_backup_link(client, message, user_id):
    backup_link = message.text.strip()
    try:
        await save_user_settings(user_id, "backup_link", backup_link)
        await message.reply("Backup link set successfully!")
    except Exception as e:
        logger.error(f"Error setting backup link: {e}")
        await message.reply("Invalid link!")
    await message.reply(
        "What next?",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Go Back", callback_data="main_menu")]])
    )
