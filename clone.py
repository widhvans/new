from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database import media_collection
from channel import get_user_settings
from shortener import get_shortlink
from utils import clean_file_name
from bot import app, logger

@app.on_callback_query(filters.regex("clone_search"))
async def clone_search(client, callback):
    user_id = callback.from_user.id
    logger.info(f"Clone search initiated by user {user_id}")
    try:
        await callback.message.edit(
            "Send search query to find files across connected users.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Go Back", callback_data="main_menu")]])
        )
        await save_user_settings(user_id, "input_state", "clone_search")
        logger.info(f"Waiting for clone search query from user {user_id}")
    except Exception as e:
        logger.error(f"Error in clone_search: {e}")
        await callback.message.edit("Error occurred. Try again.")

@app.on_message(filters.text & filters.private)
async def search_files(client, message):
    user_id = message.from_user.id
    logger.info(f"Search query received from user {user_id}: {message.text}")
    try:
        settings = await get_user_settings(user_id)
        if settings.get("input_state") != "clone_search":
            logger.info(f"No clone search expected for user {user_id}")
            return
        query = clean_file_name(message.text.strip())
        files = media_collection.find({"file_name": {"$regex": query, "$options": "i"}}).limit(10)
        buttons = []
        async for file in files:
            owner_id = file["user_id"]
            settings_owner = await get_user_settings(owner_id)
            short_link = await get_shortlink(file["raw_link"], owner_id)
            buttons.append([InlineKeyboardButton(
                f"{file['file_name']} ({file.get('file_size', 0) / 1024 / 1024:.2f} MB)",
                callback_data=f"clone_file_{file['file_id']}_{owner_id}"
            )])
        await save_user_settings(user_id, "input_state", None)
        if buttons:
            await message.reply("Found files:", reply_markup=InlineKeyboardMarkup(buttons))
            logger.info(f"Search results displayed for user {user_id}")
        else:
            await message.reply("No files found.")
            logger.info(f"No search results for user {user_id}")
    except Exception as e:
        logger.error(f"Error searching files for user {user_id}: {e}")
        await message.reply("Error occurred. Try again.")

@app.on_callback_query(filters.regex(r"clone_file_(.+)_(\d+)"))
async def clone_file(client, callback):
    user_id = callback.from_user.id
    logger.info(f"Clone file requested by user {user_id}: {callback.data}")
    try:
        file_id, owner_id = callback.data.split("_")[2:4]
        file = await media_collection.find_one({"file_id": file_id, "user_id": int(owner_id)})
        if not file:
            await callback.message.edit("File not found!")
            logger.warning(f"File {file_id} not found for user {user_id}")
            return
        settings = await get_user_settings(user_id)
        short_link = await get_shortlink(file["raw_link"], user_id)
        backup_link = settings.get("backup_link", "")
        howto_link = settings.get("howto_link", "")
        buttons = []
        if backup_link:
            buttons.append([InlineKeyboardButton("Backup Link", url=backup_link)])
        if howto_link:
            buttons.append([InlineKeyboardButton("How to Download", url=howto_link)])
        await callback.message.edit(
            f"{file['file_name']}\nSize: {file.get('file_size', 0) / 1024 / 1024:.2f} MB\n{short_link}",
            reply_markup=InlineKeyboardMarkup(buttons) if buttons else None
        )
        logger.info(f"Clone file details sent to user {user_id}")
    except Exception as e:
        logger.error(f"Error in clone_file for user {user_id}: {e}")
        await callback.message.edit("Error occurred. Try again.")
