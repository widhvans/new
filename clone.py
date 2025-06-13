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
    await callback.message.edit(
        "Send search query to find files across connected users.",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Go Back", callback_data="main_menu")]])
    )

@app.on_message(filters.text & filters.private)
async def search_files(client, message):
    user_id = message.from_user.id
    query = clean_file_name(message.text.strip())
    files = media_collection.find({"file_name": {"$regex": query, "$options": "i"}}).limit(10)
    buttons = []
    async for file in files:
        owner_id = file["user_id"]
        settings = await get_user_settings(owner_id)
        short_link = await get_shortlink(file["raw_link"], owner_id)
        buttons.append([InlineKeyboardButton(
            f"{file['file_name']} ({file.get('file_size', 0) / 1024 / 1024:.2f} MB)",
            callback_data=f"clone_file_{file['file_id']}_{owner_id}"
        )])
    if buttons:
        await message.reply("Found files:", reply_markup=InlineKeyboardMarkup(buttons))
    else:
        await message.reply("No files found.")

@app.on_callback_query(filters.regex(r"clone_file_(.+)_(\d+)"))
async def clone_file(client, callback):
    file_id, owner_id = callback.data.split("_")[2:4]
    user_id = callback.from_user.id
    file = await media_collection.find_one({"file_id": file_id, "user_id": int(owner_id)})
    if not file:
        await callback.message.edit("File not found!")
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
