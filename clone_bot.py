from aiogram import Dispatcher, types, Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import Command
import logging
import asyncio
from database import Database
from shortener import Shortener
from config import BOT_USERNAME

logger = logging.getLogger(__name__)

class CloneSearchStates(StatesGroup):
    SEARCH_QUERY = State()

def register_clone_handlers(dp: Dispatcher, db: Database, shortener: Shortener):
    async def start_clone_bot(token):
        try:
            clone_bot = Bot(token=token)
            clone_dp = Dispatcher(bot=clone_bot, storage=dp.storage)
            register_clone_handlers(clone_dp, db, shortener)
            await clone_dp.start_polling(clone_bot, skip_updates=True)
        except Exception as e:
            logger.error(f"Failed to start clone bot: {e}")

    @dp.message(Command("start"))
    async def start_command(message: types.Message):
        user_id = message.from_user.id
        clone_bot = await db.get_clone_bot(user_id)
        if clone_bot:
            welcome_msg = (
                f"Welcome to your clone bot! 🤖\n"
                f"Parent Bot - {BOT_USERNAME}\n"
                f"Search for files in PM or groups, or use /menu to access features. 🔍"
            )
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Menu 🛠️", callback_data="main_menu")]
            ])
            await message.reply(welcome_msg, reply_markup=keyboard)
        else:
            # Handle non-clone bot users
            from handlers import start_command as main_start
            await main_start(message)

    @dp.callback_query(lambda c: c.data == "clone_search")
    async def clone_search_bot(callback: types.CallbackQuery, state: FSMContext):
        new_text = "Clone search bot activated! 🔍\nSend a file name to search in PM or groups."
        current_text = getattr(callback.message, 'text', '')
        current_markup = getattr(callback.message, 'reply_markup', None)
        new_markup = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Back to Menu ⬅️", callback_data="main_menu")]
        ])
        if current_text != new_text or current_markup != new_markup:
            await callback.message.edit_text(new_text, reply_markup=new_markup)
        await state.set_state(CloneSearchStates.SEARCH_QUERY)
        await callback.answer()

    @dp.message(CloneSearchStates.SEARCH_QUERY)
    async def search_files(message: types.Message, state: FSMContext):
        user_id = message.from_user.id
        query = message.text.strip().lower()
        if not query:
            await message.reply("Please enter a search query. 🔍")
            return

        try:
            # Search user's own files
            media_files = await db.get_user_media(user_id)
            user_results = [
                file for file in media_files
                if query in file.get("file_name", "").lower()
            ]

            # Search universal database
            universal_results = await db.db.media.find({
                "file_name": {"$regex": query, "$options": "i"}
            }).to_list(None)

            if not user_results and not universal_results:
                await message.reply("No files found for your query. 😕")
                await state.clear()
                return

            # Display user's own files
            if user_results:
                keyboard = InlineKeyboardMarkup(inline_keyboard=[])
                for file in user_results[:10]:  # Limit to 10 results
                    file_name = file["file_name"]
                    file_id = file["file_id"]
                    short_link = await shortener.get_shortlink(f"telegram://file/{file_id}", user_id)
                    size = file.get("file_size", "Unknown")
                    keyboard.inline_keyboard.append([
                        InlineKeyboardButton(text=f"{file_name} ({size}) 📄", url=short_link)
                    ])
                await message.reply(f"Found {len(user_results)} files in your database: ✅", reply_markup=keyboard)

            # Display universal search results
            if universal_results:
                keyboard = InlineKeyboardMarkup(inline_keyboard=[])
                for file in universal_results[:10]:  # Limit to 10 results
                    owner_id = file["user_id"]
                    file_name = file["file_name"]
                    file_id = file["file_id"]
                    short_link = await shortener.get_shortlink(f"telegram://file/{file_id}", user_id)
                    size = file.get("file_size", "Unknown")
                    keyboard.inline_keyboard.append([
                        InlineKeyboardButton(text=f"{file_name} ({size}) 🌐", callback_data=f"clone_file:{owner_id}:{file_id}")
                    ])
                await message.reply(f"Found {len(universal_results)} files in universal database: 🌍", reply_markup=keyboard)

            await state.clear()
        except Exception as e:
            logger.error(f"Error searching files for user {user_id}: {e}")
            await message.reply("Error searching files. Please try again later. 😕")
            await state.clear()

    @dp.callback_query(lambda c: c.data.startswith("clone_file:"))
    async def handle_clone_file(callback: types.CallbackQuery):
        user_id = callback.from_user.id
        try:
            _, owner_id, file_id = callback.data.split(":")
            owner_id = int(owner_id)
            file = await db.db.media.find_one({"user_id": owner_id, "file_id": file_id})
            if not file:
                await callback.message.reply("File not found! 😕")
                await callback.answer()
                return

            file_name = file["file_name"]
            raw_link = file["raw_link"]
            short_link = await shortener.get_shortlink(raw_link, user_id)
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
        except Exception as e:
            logger.error(f"Error handling clone file for user {user_id}: {e}")
            await callback.message.reply("Error retrieving file. Please try again later. 😕")
            await callback.answer()
