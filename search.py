from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import logger
from shortener import Shortener

class SearchManager:
    def __init__(self, db, shortener: Shortener):
        self.db = db
        self.shortener = shortener

    async def search_files(self, bot: Bot, user_id: int, query: str, chat_id: int, is_clone: bool = False):
        try:
            if is_clone:
                media = await self.db.search_media(query)
            else:
                media = await self.db.search_media(query, user_id)
            if not media:
                await bot.send_message(chat_id, f"No files found for '{query}' 😕")
                logger.info(f"No files found for query '{query}' by user {user_id}")
                return

            keyboard = InlineKeyboardMarkup(inline_keyboard=[])
            for item in media[:10]:  # Limit to 10 results
                label = f"{item['file_name']} ({item['file_size'] / 1024 / 1024:.2f} MB)"
                callback_data = f"file_{item['_id']}_{user_id}"
                keyboard.inline_keyboard.append([InlineKeyboardButton(text=label, callback_data=callback_data)])
            await bot.send_message(chat_id, f"Found {len(media)} files for '{query}':", reply_markup=keyboard)
            logger.info(f"Displayed {len(media)} search results for query '{query}' by user {user_id}")
        except Exception as e:
            logger.error(f"Error searching files for query '{query}' by user {user_id}: {e}")
            await bot.send_message(chat_id, "Failed to search files. Try again. 😕")

    async def serve_file(self, bot: Bot, user_id: int, file_id: str, chat_id: int):
        try:
            from bson import ObjectId
            media = await self.db.media.find_one({"_id": ObjectId(file_id)})
            if not media:
                await bot.send_message(chat_id, "File not found! 😕")
                logger.warning(f"File {file_id} not found for user {user_id}")
                return

            owner_id = media["user_id"]
            short_link = await self.shortener.get_shortlink(self.db, media["raw_link"], owner_id)
            settings = await self.db.get_settings(owner_id)
            caption = f"<b>{media['file_name']}</b>\nSize: {media['file_size'] / 1024 / 1024:.2f} MB"
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Download 📥", url=short_link)]
            ])
            backup_link = settings.get("backup_link", "")
            how_to_download = settings.get("how_to_download", "")
            if backup_link and backup_link.startswith("http"):
                keyboard.inline_keyboard.append([InlineKeyboardButton(text="Backup Link 🔄", url=backup_link)])
            if how_to_download and how_to_download.startswith("http"):
                keyboard.inline_keyboard.append([InlineKeyboardButton(text="How to Download ❓", url=how_to_download)])

            if media["media_type"] == "photo":
                await bot.send_photo(chat_id, media["file_id"], caption=caption, reply_markup=keyboard, parse_mode="HTML")
            elif media["media_type"] == "video":
                await bot.send_video(chat_id, media["file_id"], caption=caption, reply_markup=keyboard, parse_mode="HTML")
            else:
                await bot.send_document(chat_id, media["file_id"], caption=caption, reply_markup=keyboard, parse_mode="HTML")
            logger.info(f"Served file {media['file_name']} to user {user_id}")
        except Exception as e:
            logger.error(f"Error serving file {file_id} to user {user_id}: {e}")
            await bot.send_message(chat_id, "Failed to serve file. Try again. 😕")
