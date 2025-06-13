import asyncio
import logging
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database import media_collection
from bot import app, logger, get_user_settings, validate_channel
from shortener import get_shortlink
from utils import fetch_poster
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

@app.on_message(filters.media & filters.chat(filters.channel))
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

        # Auto-post to post channels
        post_channels = settings.get("post_channels", [])
        use_poster = settings.get("use_poster", True)
        poster_url = None
        if use_poster:
            try:
                poster_url = await fetch_poster(file_name)
            except Exception as e:
                logger.error(f"Error fetching poster for {file_name}: {e}")
        backup_link = settings.get("backup_link", "")
        howto_link = settings.get("howto_link", "")

        for channel_id in post_channels:
            try:
                is_valid, error_msg = await validate_channel(client, channel_id, user_id)
                if not is_valid:
                    logger.error(f"Cannot post to channel {channel_id}: {error_msg}")
                    await message.reply(f"Error posting to channel {channel_id}: {error_msg}")
                    continue

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
                    logger.info(f"Posted photo to channel {channel_id} for user {user_id}")
                else:
                    if media_type := getattr(media, '_client_mime_type', None):
                        if media_type.startswith('video'):
                            await client.send_video(
                                channel_id,
                                video=file_id,
                                caption=caption,
                                reply_markup=InlineKeyboardMarkup(buttons) if buttons else None
                            )
                            logger.info(f"Posted video to channel {channel_id} for user {user_id}")
                        elif media_type.startswith('audio'):
                            await client.send_audio(
                                channel_id,
                                audio=file_id,
                                caption=caption,
                                reply_markup=InlineKeyboardMarkup(buttons) if buttons else None
                            )
                            logger.info(f"Posted audio to channel {channel_id} for user {user_id}")
                        elif media_type.startswith('image'):
                            await client.send_photo(
                                channel_id,
                                photo=file_id,
                                caption=caption,
                                reply_markup=InlineKeyboardMarkup(buttons) if buttons else None
                            )
                            logger.info(f"Posted photo to channel {channel_id} for user {user_id}")
                        else:
                            await client.send_document(
                                channel_id,
                                document=file_id,
                                caption=caption,
                                reply_markup=InlineKeyboardMarkup(buttons) if buttons else None
                            )
                            logger.info(f"Posted document to channel {channel_id} for user {user_id}")
                    else:
                        await client.send_message(
                            channel_id,
                            caption,
                            reply_markup=InlineKeyboardMarkup(buttons) if buttons else None
                        )
                        logger.info(f"Posted message to channel {channel_id} for user {user_id}")
                await asyncio.sleep(20)  # Delay for episode grouping
            except Exception as e:
                logger.error(f"Error posting to channel {channel_id} for user {user_id}: {e}")
                await message.reply(f"Failed to post to channel {channel_id}: {str(e)}")

        await message.reply(f"File saved! Link: {short_link}")
        logger.info(f"Media handling completed for user {user_id}")

    except Exception as e:
        logger.error(f"Error handling media for user {user_id}: {e}")
        await message.reply("Error processing media. Please try again.")
