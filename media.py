import logging
from datetime import datetime, timedelta
import re
import asyncio
from pymongo import MongoClient

logger = logging.getLogger(__name__)
client = MongoClient("mongodb://localhost:27017/")
db = client["telegram_bot"]

async def get_database_channels(user_id):
    try:
        channels = await db.find("settings", {"user_id": user_id, "type": "database_channel"}).to_list(None)
        channel_ids = [channel["channel_id"] for channel in channels]
        logger.info(f"Database channels for user {user_id}: {channel_ids}")
        return channel_ids
    except Exception as e:
        logger.error(f"Error fetching database channels for user {user_id}: {e}")
        return []

async def get_post_channels(user_id):
    try:
        channels = await db.find("settings", {"user_id": user_id, "type": "post_channel"}).to_list(None)
        channel_ids = [channel["channel_id"] for channel in channels]
        logger.info(f"Post channels for user {user_id}: {channel_ids}")
        return channel_ids
    except Exception as e:
        logger.error(f"Error fetching post channels for user {user_id}: {e}")
        return []

async def index_media(user_id, chat_id, message, bot):
    database_channels = await get_database_channels(user_id)
    if not database_channels:
        await bot.send_message(user_id, "No database channel set. Please add one using /settings.")
        return
    if chat_id not in database_channels:
        await bot.send_message(user_id, f"This chat is not a database channel. Send media to one of these: {database_channels}")
        return
    media = message.video or message.document
    if not media:
        return
    file_id = media.file_id
    file_name = media.file_name or "Unnamed"
    file_size = media.file_size
    raw_link = f"https://t.me/{chat_id}/{message.message_id}"
    media_data = {
        "user_id": user_id,
        "file_id": file_id,
        "file_name": file_name,
        "file_size": file_size,
        "raw_link": raw_link,
        "chat_id": chat_id,
        "message_id": message.message_id,
        "timestamp": datetime.now()
    }
    try:
        await db.insert_one("media", media_data)
        logger.info(f"Indexed media {file_name} for user {user_id}")
        if re.search(r"(s\d{1,2}|season\d{1,2}|ep\d{1,2}|e\d{1,2}|part\d{1,2})", file_name.lower()):
            await group_and_post_media(user_id, media_data, bot)
        else:
            await post_media_to_channels(user_id, media_data, bot)
    except Exception as e:
        logger.error(f"Failed to index media for user {user_id}: {e}")

async def get_total_files(user_id):
    try:
        files = await db.find("media", {"user_id": user_id}).to_list(None)
        logger.info(f"Fetched {len(files)} media files for user {user_id}")
        return files
    except Exception as e:
        logger.error(f"Error fetching media files for user {user_id}: {e}")
        return []

async def group_and_post_media(user_id, media_data, bot):
    file_name = media_data["file_name"].lower()
    match = re.search(r"(s\d{1,2}|season\d{1,2}|ep\d{1,2}|e\d{1,2}|part\d{1,2})", file_name)
    if match:
        await asyncio.sleep(20)
        related_files = await db.find("media", {
            "user_id": user_id,
            "file_name": {"$regex": file_name.split(match.group(1))[0], "$options": "i"},
            "timestamp": {"$gte": datetime.now() - timedelta(seconds=30)}
        }).to_list(None)
        if related_files:
            message_text = "Grouped Media:\n"
            for file in related_files:
                shortlink = await get_shortlink(file["raw_link"], user_id)
                message_text += f"{file['file_name']} ({file['file_size']} bytes): {shortlink}\n"
            message_text += f"Backup Link: {media_data['raw_link']}"
            post_channels = await get_post_channels(user_id)
            for channel_id in post_channels:
                try:
                    await bot.send_message(channel_id, message_text)
                    logger.info(f"Posted grouped media for user {user_id} to channel {channel_id}")
                except Exception as e:
                    logger.error(f"Failed to post to channel {channel_id}: {e}")

async def post_media_to_channels(user_id, media_data, bot):
    post_channels = await get_post_channels(user_id)
    if not post_channels:
        logger.info(f"No post channels configured for user {user_id}")
        return
    settings = await db.get_settings(user_id)
    if not settings.get("enable_shortlink"):
        await bot.send_message(user_id, "Please set a shortener in /settings to enable auto-posting.")
        return
    shortlink = await get_shortlink(media_data["raw_link"], user_id)
    footer = f"Backup Link: {media_data['raw_link']}"
    message_text = f"{media_data['file_name']} ({media_data['file_size']} bytes)\n{shortlink}\n{footer}"
    for channel_id in post_channels:
        try:
            await bot.send_message(channel_id, message_text)
            logger.info(f"Posted media {media_data['file_name']} to channel {channel_id}")
        except Exception as e:
            logger.error(f"Failed to post to channel {channel_id}: {e}")
