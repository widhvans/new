import asyncio
import re
from datetime import datetime
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import logger
from shortener import Shortener
from imdb import Cinemagoer

class MediaManager:
    def __init__(self, db, shortener: Shortener):
        self.db = db
        self.shortener = shortener
        self.imdb = Cinemagoer()
        self.pending_posts = {}  # {user_id: {file_name_base: [media_items]}}

    def extract_metadata(self, file_name: str):
        season = re.search(r'(?:S|Season)\s*(\d+)', file_name, re.I)
        episode = re.search(r'(?:E|Episode|Ep)\s*(\d+)', file_name, re.I)
        part = re.search(r'(?:Part|P)\s*(\d+)', file_name, re.I)
        base_name = re.sub(r'(?:S|Season|E|Episode|Ep|Part|P)\s*\d+', '', file_name, flags=re.I).strip()
        return {
            "base_name": base_name,
            "season": int(season.group(1)) if season else None,
            "episode": int(episode.group(1)) if episode else None,
            "part": int(part.group(1)) if part else None
        }

    async def index_media(self, bot: Bot, user_id: int, chat_id: int, message):
        logger.info(f"Attempting to index media for user {user_id} in chat {chat_id}")
        try:
            database_channels = await self.db.get_channels(user_id, "database")
            logger.info(f"Fetched database channels for user {user_id}: {database_channels}")
            if not database_channels:
                await message.reply("No database channels set! Add one via 'Add Database Channel' and make me an admin. 🚫\nGo to 'See Database Channels' to verify your setup.")
                logger.warning(f"No database channels configured for user {user_id}")
                return False
            if chat_id not in database_channels:
                channel_titles = []
                for channel_id in database_channels:
                    try:
                        channel = await bot.get_chat(channel_id)
                        channel_titles.append(channel.title or f"Channel {channel_id}")
                    except Exception as e:
                        logger.error(f"Error fetching channel {channel_id} title: {e}")
                        channel_titles.append(f"Channel {channel_id}")
                await message.reply(
                    f"This chat is not a database channel. Please send media to one of your database channels: {', '.join(channel_titles)}. 📥\nCheck 'See Database Channels' to confirm.",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="See Database Channels 🗄️", callback_data="see_database_channels")]
                    ])
                )
                logger.warning(f"Chat {chat_id} is not a database channel for user {user_id}. Configured channels: {database_channels}")
                return False
            if not await self.check_admin_status(bot, chat_id, bot.id):
                await message.reply("I’m not an admin in this database channel. Make me an admin to index media. 🚫")
                logger.warning(f"Bot not admin in database channel {chat_id} for user {user_id}")
                return False

            file_id, file_name, media_type, file_size = None, None, None, None
            if message.photo:
                file_id = message.photo[-1].file_id
                media_type = "photo"
                file_name = f"photo_{message.message_id}.jpg"
                file_size = message.photo[-1].file_size
            elif message.video:
                file_id = message.video.file_id
                media_type = "video"
                file_name = message.video.file_name or f"video_{message.message_id}.mp4"
                file_size = message.video.file_size
            elif message.document:
                file_id = message.document.file_id
                media_type = "document"
                file_name = message.document.file_name or f"doc_{message.message_id}"
                file_size = message.document.file_size
            else:
                await message.reply("Unsupported media type. Send a photo, video, or document. 😕")
                logger.warning(f"Unsupported media type {message.content_type} from user {user_id} in chat {chat_id}")
                return False

            if file_id and file_name and file_size is not None:
                raw_link = f"telegram://file/{file_id}"
                metadata = self.extract_metadata(file_name)
                await self.db.save_media(user_id, media_type, file_id, file_name, raw_link, file_size, metadata)
                logger.info(f"Indexed media {file_name} (type: {media_type}, size: {file_size} bytes) for user {user_id} in chat {chat_id}")

                self.schedule_post(bot, user_id, {
                    "file_id": file_id,
                    "file_name": file_name,
                    "raw_link": raw_link,
                    "file_size": file_size,
                    "metadata": metadata
                })
                await message.reply("Media indexed! Will post to your channels shortly. ✅")
                return True
            else:
                await message.reply("Invalid media file. Try again. 😕")
                logger.warning(f"Invalid media details (file_id: {file_id}, file_name: {file_name}, file_size: {file_size}) from user {user_id}")
                return False
        except Exception as e:
            logger.error(f"Error indexing media for user {user_id} in chat {chat_id}: {e}", exc_info=True)
            await message.reply("Failed to index media. Try again or contact support. 😕")
            return False

    def schedule_post(self, bot: Bot, user_id: int, media_item):
        base_name = media_item["metadata"]["base_name"]
        if user_id not in self.pending_posts:
            self.pending_posts[user_id] = {}
        if base_name not in self.pending_posts[user_id]:
            self.pending_posts[user_id][base_name] = []
        self.pending_posts[user_id][base_name].append(media_item)
        logger.info(f"Scheduled post for media {base_name} for user {user_id}")
        asyncio.create_task(self.process_pending_post(bot, user_id, base_name))

    async def process_pending_post(self, bot: Bot, user_id: int, base_name: str):
        try:
            logger.info(f"Waiting 20 seconds for additional media for user {user_id}, base_name {base_name}")
            await asyncio.sleep(20)
            media_items = self.pending_posts[user_id].pop(base_name, [])
            if not media_items:
                logger.warning(f"No media items found for posting for user {user_id}, base_name {base_name}")
                return
            await self.post_media(bot, user_id, media_items)
        except Exception as e:
            logger.error(f"Error processing pending post for user {user_id}, base_name {base_name}: {e}")

    async def post_media(self, bot: Bot, user_id: int, media_items):
        logger.info(f"Posting media for user {user_id}")
        try:
            settings = await self.db.get_settings(user_id)
            use_poster = settings.get("use_poster", True)
            shortener_enabled = settings.get("enable_shortlink", True)
            shortener_settings = await self.db.get_shortener(user_id)
            post_channels = await self.db.get_channels(user_id, "post")
            logger.info(f"Post channels for user {user_id}: {post_channels}")
            if shortener_enabled and (not shortener_settings or not shortener_settings.get("url") or not shortener_settings.get("api")):
                logger.warning(f"Invalid or missing shortener settings for user {user_id}. Posting raw links.")
                shortener_enabled = False
            if not post_channels:
                logger.warning(f"No post channels configured for user {user_id}")
                return

            base_name = media_items[0]["metadata"]["base_name"]
            poster_url = None
            if use_poster:
                try:
                    movie = self.imdb.search_movie(base_name)[0]
                    self.imdb.update(movie, ['cover'])
                    poster_url = movie.get('cover url')
                    logger.info(f"Fetched poster for {base_name}: {poster_url}")
                except Exception as e:
                    logger.warning(f"Failed to fetch poster for {base_name}: {e}")

            caption = f"<b>{base_name}</b>\n\n"
            keyboard = InlineKeyboardMarkup(inline_keyboard=[])
            for item in sorted(media_items, key=lambda x: (x["metadata"]["season"] or 0, x["metadata"]["episode"] or 0, x["metadata"]["part"] or 0)):
                link = item["raw_link"] if not shortener_enabled else await self.shortener.get_shortlink(self.db, item["raw_link"], user_id)
                label = item["file_name"]
                if item["metadata"]["season"]:
                    label = f"S{item['metadata']['season']:02d}"
                    if item["metadata"]["episode"]:
                        label += f"E{item['metadata']['episode']:02d}"
                elif item["metadata"]["part"]:
                    label = f"Part {item['metadata']['part']}"
                caption += f"{label} ({item['file_size'] / 1024 / 1024:.2f} MB): <a href='{link}'>Download</a>\n"
                keyboard.inline_keyboard.append([InlineKeyboardButton(text=f"Download {label}", url=link)])

            backup_link = settings.get("backup_link", "")
            how_to_download = settings.get("how_to_download", "")
            if backup_link and backup_link.startswith("http"):
                keyboard.inline_keyboard.append([InlineKeyboardButton(text="Backup Link 🔄", url=backup_link)])
            if how_to_download and how_to_download.startswith("http"):
                keyboard.inline_keyboard.append([InlineKeyboardButton(text="How to Download ❓", url=how_to_download)])

            for channel_id in post_channels:
                try:
                    if not await self.check_admin_status(bot, channel_id, bot.id):
                        logger.warning(f"Bot not admin in post channel {channel_id} for user {user_id}")
                        continue
                    if poster_url and use_poster:
                        await bot.send_photo(channel_id, poster_url, caption=caption, reply_markup=keyboard, parse_mode="HTML")
                        logger.info(f"Posted media group {base_name} with poster to channel {channel_id} for user {user_id}")
                    else:
                        await bot.send_message(channel_id, caption, reply_markup=keyboard, parse_mode="HTML")
                        logger.info(f"Posted media group {base_name} to channel {channel_id} for user {user_id}")
                except Exception as e:
                    logger.error(f"Failed to post media group {base_name} to channel {channel_id} for user {user_id}: {e}")
        except Exception as e:
            logger.error(f"Error posting media for user {user_id}: {e}")
