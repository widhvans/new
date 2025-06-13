import asyncio
import logging
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database import media_collection
from bot import app, logger, get_user_settings, validate_channel
from shortener import get_shortlink
from utils import fetch_poster, clean_file_name
from config import BOT_USERNAME

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='bot.log'
)

async def save_media(user_id, file_id, file_name, file_size, raw_link, short_link, channel_id):
    logger.info(f"Saving media for user {user_id}: {file_name}")
    try:
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
        logger.info(f"Media {file_name} saved for user {user_id}")
    except Exception as e:
        logger.error(f"Error saving media for user {user_id}: {e}")
        raise

async def group_episodes(files, user_id, post_channel_id, client, settings):
    logger.info(f"Grouping episodes for user {user_id} in post channel {post_channel_id}")
    try:
        use_poster = settings.get("use_poster", True)
        backup_link = settings.get("backup_link", "")
        howto_link = settings.get("howto_link", "")
        grouped = {}
        
        # Group files by cleaned name (ignoring episode/season tags)
        for file in files:
            cleaned_name = clean_file_name(file['file_name'])
            if cleaned_name not in grouped:
                grouped[cleaned_name] = []
            grouped[cleaned_name].append(file)

        for cleaned_name, group in grouped.items():
            # Fetch poster for the group
            poster_url = None
            if use_poster:
                try:
                    poster_url = await fetch_poster(cleaned_name)
                except Exception as e:
                    logger.error(f"Error fetching poster for {cleaned_name}: {e}")

            # Build caption with all episode links
            caption = f"{cleaned_name}\n\n"
            for file in sorted(group, key=lambda x: x['file_name']):
                caption += f"{file['file_name']} ({file['file_size'] / 1024 / 1024:.2f} MB): {file['short_link']}\n"
            caption += f"\nSize: {sum(f['file_size'] for f in group) / 1024 / 1024:.2f} MB"

            buttons = []
            if backup_link:
                buttons.append([InlineKeyboardButton("Backup Link", url=backup_link)])
            if howto_link:
                buttons.append([InlineKeyboardButton("How to Download", url=howto_link)])

            # Post to channel
            if poster_url:
                await client.send_photo(
                    post_channel_id,
                    photo=poster_url,
                    caption=caption,
                    reply_markup=InlineKeyboardMarkup(buttons) if buttons else None
                )
                logger.info(f"Posted grouped photo to channel {post_channel_id} for user {user_id}")
            else:
                await client.send_message(
                    post_channel_id,
                    caption,
                    reply_markup=InlineKeyboardMarkup(buttons) if buttons else None
                )
                logger.info(f"Posted grouped message to channel {post_channel_id} for user {user_id}")

    except Exception as e:
        logger.error(f"Error grouping episodes for user {user_id}: {e}")
        raise

@app.on_message(filters.media & filters.channel)
async def handle_media(client, message):
    logger.info(f"Media received in channel {message.chat.id} from user {message.from_user.id if message.from_user else 'Unknown'}")
    try:
        user_id = message.from_user.id if message.from_user else None
        if not user_id:
            logger.warning(f"Anonymous media in channel {message.chat.id}, ignoring")
            return

        settings = await get_user_settings(user_id)
        db_channels = settings.get("db_channels", [])
        if str(message.chat.id) not in db_channels:
            logger.info(f"Channel {message.chat.id} not in user's db_channels: {db_channels}")
            return

        # Extract media details
        media = message.media
        file_id = media.file_id
        file_name = getattr(media, 'file_name', f"Unnamed_{file_id}")
        file_size = getattr(media, 'file_size', 0)
        raw_link = f"https://t.me/{BOT_USERNAME}?start=file_{file_id}"
        
        # Generate short link
        try:
            short_link = await get_shortlink(raw_link, user_id)
            if short_link == raw_link:
                logger.warning(f"Shortener failed for user {user_id}, using raw link")
        except Exception as e:
            logger.error(f"Error generating short link for user {user_id}: {e}")
            short_link = raw_link

        # Save media to database
        await save_media(user_id, file_id, file_name, file_size, raw_link, short_link, str(message.chat.id))

        # Auto-post to post channels with episode grouping
        post_channels = settings.get("post_channels", [])
        if post_channels:
            # Collect files within 20 seconds for grouping
            files = [{"file_id": file_id, "file_name": file_name, "file_size": file_size, "short_link": short_link}]
            start_time = asyncio.get_event_loop().time()
            while asyncio.get_event_loop().time() - start_time < 20:
                await asyncio.sleep(1)
                new_files = await media_collection.find({
                    "user_id": user_id,
                    "channel_id": str(message.chat.id),
                    "timestamp": {"$gte": start_time}
                }).to_list(10)
                files = [
                    {"file_id": f["file_id"], "file_name": f["file_name"], "file_size": f["file_size"], "short_link": f["short_link"]}
                    for f in new_files
                ]

            for channel_id in post_channels:
                try:
                    is_valid, error_msg = await validate_channel(client, channel_id, user_id)
                    if not is_valid:
                        logger.error(f"Cannot post to channel {channel_id}: {error_msg}")
                        await message.reply(f"Error posting to channel {channel_id}: {error_msg}")
                        continue
                    await group_episodes(files, user_id, channel_id, client, settings)
                except Exception as e:
                    logger.error(f"Error posting to channel {channel_id} for user {user_id}: {e}")
                    await message.reply(f"Failed to post to channel {channel_id}: {str(e)}")

        await message.reply(f"File saved! Link: {short_link}")
        logger.info(f"Media handling completed for user {user_id}")

    except Exception as e:
        logger.error(f"Error handling media for user {user_id}: {e}")
        await message.reply("Error processing media. Please try again.")
