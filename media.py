import asyncio
from pyrogram import Client, filters
from database import media_collection
from channel import get_user_settings
from shortener import get_shortlink
from bot import app, logger
from utils import fetch_poster

async def save_media(user_id, file_id, file_name, file_size, raw_link, short_link, channel_id):
    await media_collection.insert_one({
        "user_id": user_id,
        "file_id": file_id,
        "file_name": file_name,
        "file_size": file_size,
        "raw_link": raw_link,
        "short_link": short_link,
        "channel_id": channel_id,
        "timestamp": asyncio.get_event_loop().time()
    })

@app.on_message(filters.media & filters.chat(filters.channel))
async def handle_media(client, message):
    user_id = message.from_user.id
    settings = await get_user_settings(user_id)
    db_channels = settings.get("db_channels", [])
    if str(message.chat.id) not in db_channels:
        return
    file_id = message.media.file_id
    file_name = message.media.file_name or "Unnamed File"
    file_size = message.media.file_size or 0
    raw_link = f"https://t.me/{(await client.get_me()).username}?start=file_{file_id}"
    short_link = await get_shortlink(raw_link, user_id)
    await save_media(user_id, file_id, file_name, file_size, raw_link, short_link, str(message.chat.id))
    
    # Auto-post to post channels
    post_channels = settings.get("post_channels", [])
    use_poster = settings.get("use_poster", True)
    poster_url = await fetch_poster(file_name) if use_poster else None
    backup_link = settings.get("backup_link", "")
    howto_link = settings.get("howto_link", "")
    
    for channel_id in post_channels:
        try:
            buttons = []
            if backup_link:
                buttons.append([InlineKeyboardButton("Backup Link", url=backup_link)])
            if howto_link:
                buttons.append([InlineKeyboardButton("How to Download", url=howto_link)])
            caption = f"{file_name}\nSize: {file_size / 1024 / 1024:.2f} MB\n{short_link}"
            if poster_url:
                await client.send_photo(
                    channel_id,
                    photo=poster_url,
                    caption=caption,
                    reply_markup=InlineKeyboardMarkup(buttons) if buttons else None
                )
            else:
                await client.send_message(
                    channel_id,
                    caption,
                    reply_markup=InlineKeyboardMarkup(buttons) if buttons else None
                )
            await asyncio.sleep(20)  # Delay to group episodes
        except Exception as e:
            logger.error(f"Error posting to {channel_id}: {e}")
    
    await message.reply(f"File saved! Link: {short_link}")
