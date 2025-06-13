from aiogram import Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import logging
from database import Database
from shortener import Shortener

logger = logging.getLogger(__name__)

def register_clone_handlers(dp: Dispatcher, db: Database, shortener: Shortener):
    @dp.callback_query(lambda c: c.data == "clone_search")
    async def clone_search_bot(callback: types.CallbackQuery):
        new_text = "Clone search bot activated! 🔍 Search for files in PM or connected groups."
        current_text = getattr(callback.message, 'text', '')
        current_markup = getattr(callback.message, 'reply_markup', None)
        new_markup = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Back to Menu ⬅️", callback_data="main_menu")]
        ])
        if current_text != new_text or current_markup != new_markup:
            await callback.message.edit_text(new_text, reply_markup=new_markup)
        await callback.answer()

    @dp.message(lambda message: message.chat.type in ["private", "group", "supergroup"])
    async def search_files(message: types.Message):
        user_id = message.from_user.id
        query = message.text.strip().lower()
        if not query:
            await message.reply("Please enter a search query. 🔍")
            return

        # Search media in user's database
        media_files = await db.get_user_media(user_id)
        results = [
            file for file in media_files
            if query in file.get("file_name", "").lower()
        ]

        # Search universal database (all users' files)
        universal_results = await db.db.media.find({
            "file_name": {"$regex": query, "$options": "i"}
        }).to_list(None)

        if not results and not universal_results:
            await message.reply("No files found for your query. 😕")
            return

        # Display user's own files
        if results:
            keyboard = InlineKeyboardMarkup(inline_keyboard=[])
            for file in results[:10]:  # Limit to 10 results
                file_name = file["file_name"]
                file_id = file["file_id"]
                short_link = await shortener.get_shortlink(f"telegram://file/{file_id}", user_id)
                size = file.get("file_size", "Unknown")
                keyboard.inline_keyboard.append([
                    InlineKeyboardButton(text=f"{file_name} ({size}) 📄", url=short_link)
                ])
            await message.reply(f"Found {len(results)} files in your database: ✅", reply_markup=keyboard)

        # Display universal search results for clone bot
        if universal_results:
            keyboard = InlineKeyboardMarkup(inline_keyboard=[])
            for file in universal_results[:10]:  # Limit to 10 results
                owner_id = file["user_id"]
                file_name = file["file_name"]
                file_id = file["file_id"]
                # Use the owner's shortener
                short_link = await shortener.get_shortlink(f"telegram://file/{file_id}", owner_id)
                size = file.get("file_size", "Unknown")
                keyboard.inline_keyboard.append([
                    InlineKeyboardButton(text=f"{file_name} ({size}) 🌐", callback_data=f"clone_file:{owner_id}:{file_id}")
                ])
            await message.reply(f"Found {len(universal_results)} files in universal database: 🌍", reply_markup=keyboard)

    @dp.callback_query(lambda c: c.data.startswith("clone_file:"))
    async def handle_clone_file(callback: types.CallbackQuery):
        user_id = callback.from_user.id
        _, owner_id, file_id = callback.data.split(":")
        owner_id = int(owner_id)
        file = await db.db.media.find_one({"user_id": owner_id, "file_id": file_id})
        if not file:
            await callback.message.reply("File not found! 😕")
            await callback.answer()
            return

        file_name = file["file_name"]
        raw_link = file["raw_link"]
        short_link = await shortener.get_shortlink(raw_link, user_id)  # Use requesting user's shortener
        size = file.get("file_size", "Unknown")
        backup_link = (await db.get_settings(user_id)).get("backup_link", "")

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Download 📥", url=short_link)]
        ])
        if backup_link:
            keyboard.inline_keyboard.append([InlineKeyboardButton(text="Backup Link 🔄", url=backup_link)])

        await callback.message.reply(
            f"File: {file_name} ({size}) 📄\nLink generated with your shortener! ✅",
            reply_markup=keyboard
        )
        await callback.answer()
