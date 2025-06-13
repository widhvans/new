from aiogram import Dispatcher, types, Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import Command
import logging
from database import Database
from shortener import Shortener
from search import SearchManager
from config import MONGO_URI, logger

class CloneBotStates(StatesGroup):
    SEARCH = State()

def register_clone_handlers(dp: Dispatcher, db: Database, shortener: Shortener, bot: Bot):
    search_manager = SearchManager(db, shortener)

    @dp.message(Command("start"))
    async def start_command(message: types.Message, state: FSMContext):
        user_id = message.from_user.id
        logger.info(f"Clone bot user {user_id} initiated /start")
        await state.clear()
        clone_bot = await db.get_clone_bot(user_id)
        if not clone_bot or clone_bot.get('username', 'Unknown') != f"@{bot.get_me().username}":
            await message.reply("This bot is not registered for you. Please set it up via the main bot's 'Get Your Search Bot' option. 😕")
            logger.warning(f"Unauthorized access to clone bot by user {user_id}")
            return
        welcome_msg = (
            f"Welcome to your Search Bot! 🔍\n\n"
            "I can search for files in your database or across all users' files.\n"
            "Just send a file name to start searching!"
        )
        try:
            await message.reply(welcome_msg, parse_mode="HTML")
            logger.info(f"Sent start message to user {user_id}")
        except Exception as e:
            logger.error(f"Failed to send start message to user {user_id}: {e}")

    @dp.message()
    async def handle_search_query(message: types.Message, state: FSMContext):
        user_id = message.from_user.id
        query = message.text.strip()
        chat_id = message.chat.id
        logger.info(f"Clone bot user {user_id} searching for '{query}' in chat {chat_id}")
        try:
            clone_bot = await db.get_clone_bot(user_id)
            if not clone_bot or clone_bot.get('username', 'Unknown') != f"@{bot.get_me().username}":
                await message.reply("This bot is not registered for you. Please set it up via the main bot's 'Get Your Search Bot' option. 😕")
                logger.warning(f"Unauthorized search attempt by user {user_id}")
                return
            await search_manager.search_files(bot, user_id, query, chat_id, is_clone=True)
            await state.clear()
        except Exception as e:
            logger.error(f"Error processing search query '{query}' for user {user_id}: {e}")
            await message.reply("Failed to search files. Try again. 😕")

    @dp.callback_query(lambda c: c.data.startswith("file_"))
    async def serve_file(callback: types.CallbackQuery):
        user_id = callback.from_user.id
        data = callback.data.split("_")
        file_id = data[1]
        target_user_id = int(data[2])
        logger.info(f"Clone bot user {user_id} requesting file {file_id}")
        try:
            clone_bot = await db.get_clone_bot(user_id)
            if not clone_bot or clone_bot.get('username', 'Unknown') != f"@{bot.get_me().username}":
                await callback.message.reply("This bot is not registered for you. Please set it up via the main bot's 'Get Your Search Bot' option. 😕")
                logger.warning(f"Unauthorized file request by user {user_id}")
                await callback.answer()
                return
            await search_manager.serve_file(bot, target_user_id, file_id, callback.message.chat.id)
            await callback.answer()
        except Exception as e:
            logger.error(f"Error serving file {file_id} to user {user_id}: {e}")
            await callback.message.reply("Failed to serve file. Try again. 😕")
            await callback.answer()
