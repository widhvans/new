from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from config import logger

class ChannelManager:
    def __init__(self, db):
        self.db = db

    async def connect_channel(self, bot: Bot, user_id: int, channel_id: int, channel_type: str, state: FSMContext):
        try:
            channel = await bot.get_chat(channel_id)
            channel_name = channel.title or "Unnamed Channel"
            existing_channels = await self.db.get_channels(user_id, channel_type)
            if channel_id in existing_channels:
                await bot.send_message(user_id, f"Channel {channel_name} is already connected as a {channel_type} channel! ✅", reply_markup=await self.get_main_menu(user_id))
                logger.info(f"{channel_type} channel {channel_id} already connected for user {user_id}")
                await state.clear()
                return False
            if len(existing_channels) >= 5:
                await bot.send_message(user_id, f"Max 5 {channel_type} channels allowed! 🚫", reply_markup=await self.get_main_menu(user_id))
                logger.warning(f"User {user_id} exceeded {channel_type} channel limit")
                await state.clear()
                return False
            if not await self.check_admin_status(bot, channel_id, bot.id):
                await bot.send_message(user_id, f"I’m not an admin in channel {channel_name}. Make me an admin and try again. 🚫", reply_markup=await self.get_main_menu(user_id))
                logger.warning(f"Bot not admin in channel {channel_id} for user {user_id}")
                await state.clear()
                return False
            await self.db.save_channel(user_id, channel_type, channel_id)
            await bot.send_message(user_id, f"Channel {channel_name} connected as {channel_type} channel! ✅", reply_markup=await self.get_main_menu(user_id))
            logger.info(f"Connected {channel_type} channel {channel_id} ({channel_name}) for user {user_id}")
            await state.clear()
            return True
        except Exception as e:
            logger.error(f"Error connecting {channel_type} channel {channel_id} for user {user_id}: {e}")
            await bot.send_message(user_id, f"Failed to connect channel {channel_id}. Check the ID and try again. 😕", reply_markup=await self.get_main_menu(user_id))
            await state.clear()
            return False

    async def get_main_menu(self, user_id: int):
        post_channels = await self.db.get_channels(user_id, "post")
        database_channels = await self.db.get_channels(user_id, "database")
        has_post_channels = len(post_channels) > 0
        has_database_channels = len(database_channels) > 0
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="📢 Add More Post Channels" if has_post_channels else "📢 Add Post Channel", callback_data="add_post_channel"),
                InlineKeyboardButton(text="🗄️ Add More Database Channels" if has_database_channels else "🗄️ Add Database Channel", callback_data="add_database_channel")
            ],
            [
                InlineKeyboardButton(text="📋 See Post Channels", callback_data="see_post_channels"),
                InlineKeyboardButton(text="📋 See Database Channels", callback_data="see_database_channels")
            ],
            [
                InlineKeyboardButton(text="🔗 Change Shortener", callback_data="set_shortener"),
                InlineKeyboardButton(text="👀 See Shortener", callback_data="see_shortener")
            ],
            [
                InlineKeyboardButton(text="🔄 Set Backup Link", callback_data="set_backup_link"),
                InlineKeyboardButton(text="📖 Set How to Download", callback_data="set_how_to_download")
            ],
            [
                InlineKeyboardButton(text="📊 Total Files", callback_data="total_files"),
                InlineKeyboardButton(text="🤖 Get Your Search Bot", callback_data="get_search_bot")
            ],
            [
                InlineKeyboardButton(text="🔍 Clone Search", callback_data="clone_search"),
                InlineKeyboardButton(text="🚫 Set FSub", callback_data="set_fsub")
            ]
        ])
        return keyboard

    async def check_admin_status(self, bot: Bot, channel_id: int, bot_id: int, retries=3, delay=2):
        for attempt in range(retries):
            try:
                bot_member = await bot.get_chat_member(channel_id, bot_id)
                if bot_member.status in ["administrator", "creator"]:
                    logger.info(f"Confirmed bot is admin in channel {channel_id}, attempt {attempt + 1}")
                    return True
                logger.warning(f"Bot not admin in channel {channel_id}, attempt {attempt + 1}/{retries}")
            except Exception as e:
                logger.error(f"Error checking admin status in channel {channel_id}, attempt {attempt + 1}/{retries}: {e}")
            await asyncio.sleep(delay * (2 ** attempt))
        return False
