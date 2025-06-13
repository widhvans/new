from aiogram import Dispatcher, types, Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import Command, StateFilter, BaseFilter
import asyncio
import logging
from database import Database
from shortener import Shortener
from config import BOT_USERNAME

logger = logging.getLogger(__name__)

class BotStates(StatesGroup):
    SET_POST_CHANNEL = State()
    SET_DATABASE_CHANNEL = State()
    SET_SHORTENER = State()
    SET_BACKUP_LINK = State()
    SET_HOW_TO_DOWNLOAD = State()
    SET_CLONE_TOKEN = State()

class MediaFilter(BaseFilter):
    async def __call__(self, message: types.Message) -> bool:
        return message.content_type in [types.ContentType.PHOTO, types.ContentType.VIDEO, types.ContentType.DOCUMENT]

async def check_admin_status(bot: Bot, channel_id: int, bot_id: int, retries=3, delay=2):
    for attempt in range(retries):
        try:
            bot_member = await bot.get_chat_member(channel_id, bot_id)
            if bot_member.status in ["administrator", "creator"]:
                logger.info(f"Confirmed bot is admin in channel {channel_id}, attempt {attempt + 1}")
                return True
            logger.warning(f"Bot not admin in channel {channel_id}, attempt {attempt + 1}/{retries}")
        except Exception as e:
            logger.error(f"Error checking admin status in channel {channel_id}, attempt {attempt + 1}/{retries}: {e}")
        await asyncio.sleep(delay * (2 ** attempt))  # Exponential backoff
    return False

async def connect_channel(bot: Bot, user_id: int, channel_id: int, channel_type: str, state: FSMContext):
    try:
        channel = await bot.get_chat(channel_id)
        channel_name = channel.title or "Unnamed Channel"
        existing_channels = await db_instance.get_channels(user_id, channel_type)
        if channel_id in existing_channels:
            await bot.send_message(user_id, f"Channel {channel_name} is already connected as a {channel_type} channel! ✅", reply_markup=await get_main_menu(user_id))
            logger.info(f"{channel_type} channel {channel_id} already connected for user {user_id}")
            await state.clear()
            return False
        if len(existing_channels) >= 5:
            await bot.send_message(user_id, f"Max 5 {channel_type} channels allowed! 🚫", reply_markup=await get_main_menu(user_id))
            logger.warning(f"User {user_id} exceeded {channel_type} channel limit")
            await state.clear()
            return False
        if not await check_admin_status(bot, channel_id, bot.id):
            await bot.send_message(user_id, f"I’m not an admin in channel {channel_name}. Make me an admin and try again. 🚫", reply_markup=await get_main_menu(user_id))
            logger.warning(f"Bot not admin in channel {channel_id} for user {user_id}")
            await state.clear()
            return False
        await db_instance.save_channel(user_id, channel_type, channel_id)
        await bot.send_message(user_id, f"Channel {channel_name} connected as {channel_type} channel! ✅", reply_markup=await get_main_menu(user_id))
        logger.info(f"Connected {channel_type} channel {channel_id} ({channel_name}) for user {user_id}")
        await state.clear()
        return True
    except Exception as e:
        logger.error(f"Error connecting {channel_type} channel {channel_id} for user {user_id}: {e}")
        await bot.send_message(user_id, f"Failed to connect channel {channel_id}. Check the ID and try again. 😕", reply_markup=await get_main_menu(user_id))
        await state.clear()
        return False

async def get_main_menu(user_id: int):
    post_channels = await db_instance.get_channels(user_id, "post")
    database_channels = await db_instance.get_channels(user_id, "database")
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
            InlineKeyboardButton(text="🔍 Clone Search", callback_data="clone_search")
        ],
        [
            InlineKeyboardButton(text="🤖 Add Clone Bot", callback_data="add_clone"),
            InlineKeyboardButton(text="📋 My Clones", callback_data="my_clones")
        ]
    ])
    return keyboard

async def test_shortener(db: Database, shortener: Shortener, user_id: int):
    try:
        test_url = "https://example.com"
        short_link = await shortener.get_shortlink(db, test_url, user_id)
        if short_link and short_link.startswith("http"):
            return short_link
        logger.warning(f"Failed to generate test shortlink for user {user_id}")
        return None
    except Exception as e:
        logger.error(f"Error testing shortener for user {user_id}: {e}")
        return None

def register_handlers(dp: Dispatcher, db: Database, shortener: Shortener, bot: Bot):
    global db_instance
    db_instance = db
    ADMINS = [123456789]  # Replace with actual admin IDs

    @dp.message(Command("start"))
    async def start_command(message: types.Message, state: FSMContext):
        user_id = message.from_user.id
        logger.info(f"User {user_id} initiated /start")
        await state.clear()
        welcome_msg = (
            "Welcome to your personal storage bot! 📦\n"
            "Save media, auto-post to channels, and more.\n"
            "To connect channels, use the menu, make me an admin, and send the channel ID.\n"
            "Let's get started! 🚀"
        )
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Let's Begin! ▶️", callback_data="main_menu")]
        ])
        try:
            await message.reply(welcome_msg, reply_markup=keyboard)
            logger.info(f"Sent start message to user {user_id}")
        except Exception as e:
            logger.error(f"Failed to send start message to user {user_id}: {e}")

    @dp.callback_query(lambda c: c.data == "main_menu")
    async def show_main_menu(callback: types.CallbackQuery, state: FSMContext):
        user_id = callback.from_user.id
        logger.info(f"User {user_id} requested main menu")
        await state.clear()
        new_text = "Choose an option: 🛠️"
        try:
            await callback.message.edit_text(new_text, reply_markup=await get_main_menu(user_id))
            logger.info(f"Displayed main menu for user {user_id}")
            await callback.answer()
        except Exception as e:
            logger.error(f"Failed to show main menu for user {user_id}: {e}")
            await callback.message.reply("Failed to show menu. Try again. 😕", reply_markup=await get_main_menu(user_id))

    @dp.callback_query(lambda c: c.data == "add_post_channel")
    async def add_post_channel(callback: types.CallbackQuery, state: FSMContext):
        user_id = callback.from_user.id
        logger.info(f"User {user_id} adding post channel")
        try:
            channels = await db_instance.get_channels(user_id, "post")
            if len(channels) >= 5:
                await callback.message.edit_text("Max 5 post channels allowed! 🚫", reply_markup=await get_main_menu(user_id))
                logger.warning(f"User {user_id} exceeded post channel limit")
                await callback.answer()
                return
            await state.set_state(BotStates.SET_POST_CHANNEL)
            logger.info(f"Set FSM state SET_POST_CHANNEL for user {user_id}")
            await callback.message.edit_text(
                "Make me an admin in your post channel (public or private), then send the channel ID (e.g., -100123456789). 📢",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="Cancel ❌", callback_data="cancel_add_channel")]
                ])
            )
            logger.info(f"Prompted user {user_id} to add post channel and send channel ID")
            await callback.answer()
        except Exception as e:
            logger.error(f"Failed to prompt post channel setup for user {user_id}: {e}")
            await callback.message.reply("Failed to initiate post channel setup. Try again. 😕", reply_markup=await get_main_menu(user_id))
            await state.clear()

    @dp.callback_query(lambda c: c.data == "add_database_channel")
    async def add_database_channel(callback: types.CallbackQuery, state: FSMContext):
        user_id = callback.from_user.id
        logger.info(f"User {user_id} adding database channel")
        try:
            channels = await db_instance.get_channels(user_id, "database")
            if len(channels) >= 5:
                await callback.message.edit_text("Max 5 database channels allowed! 🚫", reply_markup=await get_main_menu(user_id))
                logger.warning(f"User {user_id} exceeded database channel limit")
                await callback.answer()
                return
            await state.set_state(BotStates.SET_DATABASE_CHANNEL)
            logger.info(f"Set FSM state SET_DATABASE_CHANNEL for user {user_id}")
            await callback.message.edit_text(
                "Make me an admin in your database channel (public or private), then send the channel ID (e.g., -100123456789). 🗄️",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="Cancel ❌", callback_data="cancel_add_channel")]
                ])
            )
            logger.info(f"Prompted user {user_id} to add database channel and send channel ID")
            await callback.answer()
        except Exception as e:
            logger.error(f"Failed to prompt database channel setup for user {user_id}: {e}")
            await callback.message.reply("Failed to initiate database channel setup. Try again. 😕", reply_markup=await get_main_menu(user_id))
            await state.clear()

    @dp.callback_query(lambda c: c.data == "cancel_add_channel")
    async def cancel_add_channel(callback: types.CallbackQuery, state: FSMContext):
        user_id = callback.from_user.id
        logger.info(f"User {user_id} canceled channel addition")
        try:
            await state.clear()
            await callback.message.edit_text("Channel addition canceled. Returning to main menu... 😕", reply_markup=await get_main_menu(user_id))
            logger.info(f"Canceled channel addition for user {user_id}")
            await callback.answer()
        except Exception as e:
            logger.error(f"Error canceling channel addition for user {user_id}: {e}")
            await callback.message.reply("Failed to cancel. Try again. 😕", reply_markup=await get_main_menu(user_id))

    @dp.message(StateFilter(BotStates.SET_POST_CHANNEL, BotStates.SET_DATABASE_CHANNEL))
    async def process_channel_id(message: types.Message, state: FSMContext):
        user_id = message.from_user.id
        logger.info(f"User {user_id} sent channel ID: {message.text}")
        try:
            channel_id = int(message.text.strip())
            if not str(channel_id).startswith("-100"):
                await message.reply("Invalid channel ID format. Use format like -100123456789. 😕", reply_markup=await get_main_menu(user_id))
                logger.warning(f"Invalid channel ID format sent by user {user_id}: {message.text}")
                return
            user_state = await state.get_state()
            channel_type = "post" if user_state == BotStates.SET_POST_CHANNEL.state else "database"
            await connect_channel(bot, user_id, channel_id, channel_type, state)
            logger.info(f"Processed channel ID {channel_id} for user {user_id}, channel_type={channel_type}")
        except ValueError:
            await message.reply("Invalid channel ID. Please send a numeric ID like -100123456789. 😕", reply_markup=await get_main_menu(user_id))
            logger.warning(f"Non-numeric channel ID sent by user {user_id}: {message.text}")
        except Exception as e:
            logger.error(f"Error processing channel ID for user {user_id}: {e}")
            await message.reply("Failed to process channel ID. Try again. 😕", reply_markup=await get_main_menu(user_id))

    @dp.callback_query(lambda c: c.data == "see_post_channels")
    async def see_post_channels(callback: types.CallbackQuery):
        user_id = callback.from_user.id
        logger.info(f"User {user_id} viewing post channels")
        try:
            channels = await db_instance.get_channels(user_id, "post")
            if not channels:
                new_text = "No post channels connected! 🚫"
                current_text = getattr(callback.message, 'text', '')
                if current_text != new_text:
                    await callback.message.edit_text(new_text, reply_markup=await get_main_menu(user_id))
                logger.info(f"No post channels for user {user_id}")
                await callback.answer()
                return
            keyboard = InlineKeyboardMarkup(inline_keyboard=[])
            for channel_id in channels:
                channel = await bot.get_chat(channel_id)
                channel_name = channel.title or "Unnamed Channel"
                keyboard.inline_keyboard.append([
                    InlineKeyboardButton(text=f"{channel_name}", callback_data=f"view_post_{channel_id}"),
                    InlineKeyboardButton(text="🗑️ Delete", callback_data=f"delete_post_{channel_id}")
                ])
            keyboard.inline_keyboard.append([InlineKeyboardButton(text="⬅️ Back", callback_data="main_menu")])
            new_text = "Connected Post Channels:"
            current_text = getattr(callback.message, 'text', '')
            if current_text != new_text or getattr(callback.message, 'reply_markup', None) != keyboard:
                await callback.message.edit_text(new_text, reply_markup=keyboard)
            logger.info(f"Displayed {len(channels)} post channels for user {user_id}")
            await callback.answer()
        except Exception as e:
            logger.error(f"Error showing post channels for user {user_id}: {e}")
            await callback.message.reply("Failed to fetch post channels. Try again. 😕", reply_markup=await get_main_menu(user_id))

    @dp.callback_query(lambda c: c.data == "see_database_channels")
    async def see_database_channels(callback: types.CallbackQuery):
        user_id = callback.from_user.id
        logger.info(f"User {user_id} viewing database channels")
        try:
            channels = await db_instance.get_channels(user_id, "database")
            if not channels:
                new_text = "No database channels connected! 🚫"
                current_text = getattr(callback.message, 'text', '')
                if current_text != new_text:
                    await callback.message.edit_text(new_text, reply_markup=await get_main_menu(user_id))
                logger.info(f"No database channels for user {user_id}")
                await callback.answer()
                return
            keyboard = InlineKeyboardMarkup(inline_keyboard=[])
            for channel_id in channels:
                channel = await bot.get_chat(channel_id)
                channel_name = channel.title or "Unnamed Channel"
                keyboard.inline_keyboard.append([
                    InlineKeyboardButton(text=f"{channel_name}", callback_data=f"view_db_{channel_id}"),
                    InlineKeyboardButton(text="🗑️ Delete", callback_data=f"delete_db_{channel_id}")
                ])
            keyboard.inline_keyboard.append([InlineKeyboardButton(text="⬅️ Back", callback_data="main_menu")])
            new_text = "Connected Database Channels:"
            current_text = getattr(callback.message, 'text', '')
            if current_text != new_text or getattr(callback.message, 'reply_markup', None) != keyboard:
                await callback.message.edit_text(new_text, reply_markup=keyboard)
            logger.info(f"Displayed {len(channels)} database channels for user {user_id}")
            await callback.answer()
        except Exception as e:
            logger.error(f"Error showing database channels for user {user_id}: {e}")
            await callback.message.reply("Failed to fetch database channels. Try again. 😕", reply_markup=await get_main_menu(user_id))

    @dp.callback_query(lambda c: c.data.startswith("delete_post_"))
    async def delete_post_channel(callback: types.CallbackQuery):
        user_id = callback.from_user.id
        logger.info(f"User {user_id} deleting post channel")
        try:
            channel_id = int(callback.data.split("_")[2])
            channels = await db_instance.get_channels(user_id, "post")
            if channel_id not in channels:
                await callback.message.edit_text("Channel not found! 🚫", reply_markup=await get_main_menu(user_id))
                logger.warning(f"Post channel {channel_id} not found for user {user_id}")
                await callback.answer()
                return
            await db_instance.db.channels.update_one(
                {"user_id": user_id},
                {"$pull": {"post_channel_ids": channel_id}}
            )
            channel = await bot.get_chat(channel_id)
            channel_name = channel.title or "Unnamed Channel"
            await callback.message.edit_text(f"Post channel {channel_name} deleted! ✅", reply_markup=await get_main_menu(user_id))
            logger.info(f"Deleted post channel {channel_id} for user {user_id}")
            await callback.answer()
        except Exception as e:
            logger.error(f"Error deleting post channel for user {user_id}: {e}")
            await callback.message.reply("Failed to delete post channel. Try again. 😕", reply_markup=await get_main_menu(user_id))

    @dp.callback_query(lambda c: c.data.startswith("delete_db_"))
    async def delete_database_channel(callback: types.CallbackQuery):
        user_id = callback.from_user.id
        logger.info(f"User {user_id} deleting database channel")
        try:
            channel_id = int(callback.data.split("_")[2])
            channels = await db_instance.get_channels(user_id, "database")
            if channel_id not in channels:
                await callback.message.edit_text("Channel not found! 🚫", reply_markup=await get_main_menu(user_id))
                logger.warning(f"Database channel {channel_id} not found for user {user_id}")
                await callback.answer()
                return
            await db_instance.db.channels.update_one(
                {"user_id": user_id},
                {"$pull": {"database_channel_ids": channel_id}}
            )
            channel = await bot.get_chat(channel_id)
            channel_name = channel.title or "Unnamed Channel"
            await callback.message.edit_text(f"Database channel {channel_name} deleted! ✅", reply_markup=await get_main_menu(user_id))
            logger.info(f"Deleted database channel {channel_id} for user {user_id}")
            await callback.answer()
        except Exception as e:
            logger.error(f"Error deleting database channel for user {user_id}: {e}")
            await callback.message.reply("Failed to delete database channel. Try again. 😕", reply_markup=await get_main_menu(user_id))

    @dp.message(Command("shortlink"))
    async def shortlink_command(message: types.Message):
        user_id = message.from_user.id
        chat_type = message.chat.type
        grp_id = user_id if chat_type == "private" else message.chat.id
        title = "PM" if chat_type == "private" else message.chat.title
        logger.info(f"User {user_id} setting shortlink for chat {grp_id}")
        try:
            if chat_type != "private":
                member = await message.bot.get_chat_member(grp_id, user_id)
                if member.status not in ["administrator", "creator"] and str(user_id) not in ADMINS:
                    await message.reply("<b>You don't have access to this command! 🚫</b>", reply_markup=await get_main_menu(user_id))
                    logger.warning(f"User {user_id} lacks permission for /shortlink in chat {grp_id}")
                    return
            _, shortlink_url, api = message.text.split(" ")
            reply = await message.reply("<b>Please wait... ⏳</b>")
            await db_instance.save_shortener(user_id, shortlink_url, api)
            test_link = await test_shortener(db_instance, shortener, user_id)
            test_status = f"Test Link: <code>{test_link}</code>\n" if test_link else "Test Link: Failed to generate, check API settings.\n"
            await reply.edit_text(
                f"<b>Successfully added shortlink API for {title} ✅</b>\n\nCurrent shortlink website: <code>{shortlink_url}</code>\nCurrent API: <code>{api}</code>\n{test_status}",
                reply_markup=await get_main_menu(user_id),
                parse_mode="HTML"
            )
            logger.info(f"Shortlink set for user {user_id}")
        except ValueError:
            await message.reply(
                f"<b>Hey {message.from_user.mention}, command incomplete 😕</b>\n\nUse proper format!\n\n<code>/shortlink mdisk.link b6d97f6s96ds69d69d68d575d</code>",
                reply_markup=await get_main_menu(user_id),
                parse_mode="HTML"
            )
            logger.warning(f"Invalid /shortlink format by user {user_id}")
        except Exception as e:
            logger.error(f"Error setting shortlink for user {user_id}: {e}")
            await message.reply("Failed to set shortlink. Try again. 😕", reply_markup=await get_main_menu(user_id))

    @dp.message(MediaFilter())
    async def handle_media(message: types.Message):
        user_id = message.from_user.id
        chat_id = message.chat.id
        logger.info(f"User {user_id} sent media in chat {chat_id}")
        try:
            database_channels = await db_instance.get_channels(user_id, "database")
            logger.info(f"Fetched {len(database_channels)} database channels for user {user_id}")
            if not database_channels:
                logger.warning(f"No database channels configured for user {user_id}")
                await message.reply("No database channels set! Add one via 'Add Database Channel' and make me an admin. 🚫", reply_markup=await get_main_menu(user_id))
                return
            if chat_id not in database_channels:
                logger.info(f"Chat {chat_id} is not a database channel for user {user_id}")
                return
            if not await check_admin_status(message.bot, chat_id, message.bot.id):
                logger.warning(f"Bot not admin in database channel {chat_id} for user {user_id}")
                await message.reply("I’m not an admin in this database channel. Make me an admin. 🚫", reply_markup=await get_main_menu(user_id))
                return
            file_id = None
            file_name = None
            media_type = None
            file_size = None
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
                logger.warning(f"Unsupported media type from user {user_id} in chat {chat_id}")
                await message.reply("Unsupported media type. Send a photo, video, or document. 😕", reply_markup=await get_main_menu(user_id))
                return
            if file_id and file_name and file_size is not None:
                raw_link = f"telegram://file/{file_id}"
                await db_instance.save_media(user_id, media_type, file_id, file_name, raw_link, file_size)
                logger.info(f"Indexed media {file_name} (type: {media_type}, size: {file_size} bytes) for user {user_id} in chat {chat_id}")
                shortener_settings = await db_instance.get_shortener(user_id)
                post_channels = await db_instance.get_channels(user_id, "post")
                if not shortener_settings or not shortener_settings.get("url") or not shortener_settings.get("api"):
                    logger.warning(f"Invalid or missing shortener settings for user {user_id}")
                    await message.reply("Media indexed, but no valid shortener set. Configure via 'Change Shortener' to enable posting. ⚠️", reply_markup=await get_main_menu(user_id))
                elif not post_channels:
                    logger.warning(f"No post channels configured for user {user_id}")
                    await message.reply("Media indexed, but no post channels set. Add one via 'Add Post Channel' to enable posting. ⚠️", reply_markup=await get_main_menu(user_id))
                else:
                    asyncio.create_task(post_media_with_delay(bot, user_id, file_name, raw_link, user_id))
                    await message.reply("Media indexed! Will post to your channels shortly. ✅", reply_markup=await get_main_menu(user_id))
            else:
                logger.warning(f"Invalid media details (file_id: {file_id}, file_name: {file_name}, file_size: {file_size}) from user {user_id}")
                await message.reply("Invalid media file. Try again. 😕", reply_markup=await get_main_menu(user_id))
        except Exception as e:
            logger.error(f"Error indexing media for user {user_id} in chat {chat_id}: {e}")
            await message.reply("Failed to index media. Try again or contact support. 😕", reply_markup=await get_main_menu(user_id))

    async def post_media_with_delay(bot: Bot, user_id: int, file_name: str, raw_link: str, chat_id: int):
        try:
            logger.info(f"Scheduling delayed post for media {file_name} for user {user_id}")
            await asyncio.sleep(20)
            await post_media(bot, user_id, file_name, raw_link, chat_id)
        except Exception as e:
            logger.error(f"Error in delayed post_media for user {user_id}: {e}")

    async def post_media(bot: Bot, user_id: int, file_name: str, raw_link: str, chat_id: int):
        logger.info(f"Posting media {file_name} for user {user_id}")
        try:
            shortener_settings = await db_instance.get_shortener(user_id)
            if not shortener_settings or not shortener_settings.get("url") or not shortener_settings.get("api"):
                logger.warning(f"Invalid or missing shortener settings for user {user_id}")
                return
            short_link = await shortener.get_shortlink(db_instance, raw_link, user_id)
            if not short_link or not short_link.startswith("http"):
                logger.warning(f"Invalid shortlink for media {file_name}, user {user_id}")
                return
            post_channels = await db_instance.get_channels(user_id, "post")
            if not post_channels:
                logger.warning(f"No post channels configured for user {user_id}")
                return
            settings = await db_instance.get_settings(user_id)
            backup_link = settings.get("backup_link", "")
            how_to_download = settings.get("how_to_download", "")
            poster_url = await fetch_poster(file_name)
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Download 📥", url=short_link)]
            ])
            if backup_link and backup_link.startswith("http"):
                keyboard.inline_keyboard.append([InlineKeyboardButton(text="Backup Link 🔄", url=backup_link)])
            if how_to_download and how_to_download.startswith("http"):
                keyboard.inline_keyboard.append([InlineKeyboardButton(text="How to Download ❓", url=how_to_download)])
            for channel_id in post_channels:
                try:
                    if not await check_admin_status(bot, channel_id, bot.id):
                        logger.warning(f"Bot not admin in post channel {channel_id} for user {user_id}")
                        continue
                    if poster_url:
                        await bot.send_photo(channel_id, poster_url, caption=f"{file_name}\n{short_link}", reply_markup=keyboard)
                        logger.info(f"Posted media {file_name} with poster to channel {channel_id} for user {user_id}")
                    else:
                        await bot.send_message(channel_id, f"{file_name}\n{short_link}", reply_markup=keyboard)
                        logger.info(f"Posted media {file_name} to channel {channel_id} for user {user_id}")
                except Exception as e:
                    logger.error(f"Failed to post media {file_name} to channel {channel_id} for user {user_id}: {e}")
        except Exception as e:
            logger.error(f"Error posting media for user {user_id}: {e}")

    async def fetch_poster(file_name):
        logger.info(f"Fetching poster for file {file_name}")
        try:
            return None  # Implement Cinemagoer logic if needed
        except Exception as e:
            logger.error(f"Error fetching poster for file {file_name}: {e}")
            return None

    @dp.callback_query(lambda c: c.data == "total_files")
    async def show_total_files(callback: types.CallbackQuery):
        user_id = callback.from_user.id
        logger.info(f"User {user_id} checking total files")
        try:
            media_files = await db_instance.get_user_media(user_id)
            new_text = f"Total files: {len(media_files)} 📊"
            current_text = getattr(callback.message, 'text', '')
            if current_text != new_text:
                await callback.message.edit_text(new_text, reply_markup=await get_main_menu(user_id))
            await callback.answer()
            logger.info(f"Displayed total files ({len(media_files)}) for user {user_id}")
        except Exception as e:
            logger.error(f"Error showing total files for user {user_id}: {e}")
            await callback.message.reply("Failed to fetch total files. Try again. 😕", reply_markup=await get_main_menu(user_id))

    @dp.message(Command("broadcast"))
    async def broadcast_command(message: types.Message):
        user_id = message.from_user.id
        logger.info(f"User {user_id} attempting broadcast")
        try:
            if user_id not in ADMINS:
                logger.warning(f"User {user_id} not authorized for broadcast")
                return
            await message.reply("Send the broadcast message. 📢", reply_markup=await get_main_menu(user_id))
            logger.info(f"Broadcast initiated by admin {user_id}")
        except Exception as e:
            logger.error(f"Error in broadcast command for user {user_id}: {e}")

    @dp.message(Command("stats"))
    async def stats_command(message: types.Message):
        user_id = message.from_user.id
        logger.info(f"User {user_id} requesting stats")
        try:
            if user_id not in ADMINS:
                logger.warning(f"User {user_id} not authorized for stats")
                return
            total_users = await db_instance.db.users.count_documents({})
            total_db_owners = await db_instance.db.channels.count_documents({"channel_type": "database"})
            await message.reply(f"Users: {total_users}\nDatabase Owners: {total_db_owners} 📈", reply_markup=await get_main_menu(user_id))
            logger.info(f"Displayed stats for admin {user_id}")
        except Exception as e:
            logger.error(f"Error in stats command for user {user_id}: {e}")
            await message.reply("Failed to fetch stats. Try again. 😕", reply_markup=await get_main_menu(user_id))

    @dp.callback_query(lambda c: c.data == "set_shortener")
    async def set_shortener(callback: types.CallbackQuery, state: FSMContext):
        user_id = callback.from_user.id
        logger.info(f"User {user_id} setting shortener")
        try:
            await state.set_state(BotStates.SET_SHORTENER)
            await callback.message.edit_text(
                "Send the shortener details in format: <code>shortlink mdisk.link your_api_key</code> 🔗",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="Cancel ❌", callback_data="cancel_shortener")]
                ])
            )
            await callback.answer()
            logger.info(f"Prompted user {user_id} to set shortener")
        except Exception as e:
            logger.error(f"Error prompting shortener setup for user {user_id}: {e}")
            await callback.message.reply("Failed to initiate shortener setup. Try again. 😕", reply_markup=await get_main_menu(user_id))

    @dp.callback_query(lambda c: c.data == "cancel_shortener")
    async def cancel_shortener(callback: types.CallbackQuery, state: FSMContext):
        user_id = callback.from_user.id
        logger.info(f"User {user_id} canceled shortener setup")
        try:
            await state.clear()
            await callback.message.edit_text("Shortener setup canceled. Returning to main menu... 😕", reply_markup=await get_main_menu(user_id))
            logger.info(f"Canceled shortener setup for user {user_id}")
            await callback.answer()
        except Exception as e:
            logger.error(f"Error canceling shortener setup for user {user_id}: {e}")
            await callback.message.reply("Failed to cancel. Try again. 😕", reply_markup=await get_main_menu(user_id))

    @dp.message(StateFilter(BotStates.SET_SHORTENER))
    async def process_shortener(message: types.Message, state: FSMContext):
        user_id = message.from_user.id
        logger.info(f"User {user_id} processing shortener")
        try:
            _, shortlink_url, api = message.text.split(" ")
            await db_instance.save_shortener(user_id, shortlink_url, api)
            test_link = await test_shortener(db_instance, shortener, user_id)
            test_status = f"Test Link: <code>{test_link}</code>\n" if test_link else "Test Link: Failed to generate, check API settings.\n"
            await message.reply(
                f"Shortener set! ✅\nWebsite: <code>{shortlink_url}</code>\nAPI: <code>{api}</code>\n{test_status}",
                reply_markup=await get_main_menu(user_id)
            )
            await state.clear()
            logger.info(f"Shortener set for user {user_id}")
        except ValueError:
            await message.reply(
                "Invalid format! Use: <code>shortlink mdisk.link your_api_key</code> 😕",
                reply_markup=await get_main_menu(user_id)
            )
            logger.warning(f"Invalid shortener format by user {user_id}")
        except Exception as e:
            logger.error(f"Error processing shortener for user {user_id}: {e}")
            await message.reply("Failed to set shortener. Try again. 😕", reply_markup=await get_main_menu(user_id))
            await state.clear()

    @dp.callback_query(lambda c: c.data == "see_shortener")
    async def see_shortener(callback: types.CallbackQuery):
        user_id = callback.from_user.id
        logger.info(f"User {user_id} viewing shortener")
        try:
            shortener = await db_instance.get_shortener(user_id)
            new_markup = await get_main_menu(user_id)
            if shortener:
                test_link = await test_shortener(db_instance, shortener, user_id)
                test_status = f"Test Link: <code>{test_link}</code>\n" if test_link else "Test Link: Failed to generate, check API settings.\n"
                new_text = f"Current Shortener: 👀\nWebsite: <code>{shortener['url']}</code>\nAPI: <code>{shortener['api']}</code>\n{test_status}"
            else:
                new_text = "No shortener set! 🚫"
            current_text = getattr(callback.message, 'text', '')
            if current_text != new_text:
                await callback.message.edit_text(new_text, reply_markup=new_markup)
            await callback.answer()
            logger.info(f"Displayed shortener for user {user_id}")
        except Exception as e:
            logger.error(f"Error showing shortener for user {user_id}: {e}")
            await callback.message.reply("Failed to fetch shortener. Try again. 😕", reply_markup=await get_main_menu(user_id))

    @dp.callback_query(lambda c: c.data == "set_backup_link")
    async def set_backup_link(callback: types.CallbackQuery, state: FSMContext):
        user_id = callback.from_user.id
        logger.info(f"User {user_id} setting backup link")
        try:
            await state.set_state(BotStates.SET_BACKUP_LINK)
            await callback.message.edit_text(
                "Please send the backup link URL. 🔄",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="Cancel ❌", callback_data="cancel_backup_link")]
                ])
            )
            await callback.answer()
            logger.info(f"Prompted user {user_id} to set backup link")
        except Exception as e:
            logger.error(f"Error prompting backup link setup for user {user_id}: {e}")
            await callback.message.reply("Failed to initiate backup link setup. Try again. 😕", reply_markup=await get_main_menu(user_id))

    @dp.callback_query(lambda c: c.data == "cancel_backup_link")
    async def cancel_backup_link(callback: types.CallbackQuery, state: FSMContext):
        user_id = callback.from_user.id
        logger.info(f"User {user_id} canceled backup link setup")
        try:
            await state.clear()
            await callback.message.edit_text("Backup link setup canceled. Returning to main menu... 😕", reply_markup=await get_main_menu(user_id))
            logger.info(f"Canceled backup link setup for user {user_id}")
            await callback.answer()
        except Exception as e:
            logger.error(f"Error canceling backup link setup for user {user_id}: {e}")
            await callback.message.reply("Failed to cancel. Try again. 😕", reply_markup=await get_main_menu(user_id))

    @dp.message(StateFilter(BotStates.SET_BACKUP_LINK))
    async def process_backup_link(message: types.Message, state: FSMContext):
        user_id = message.from_user.id
        logger.info(f"User {user_id} processing backup link")
        try:
            backup_link = message.text.strip()
            if not backup_link.startswith("http"):
                await message.reply("Invalid URL! Send a valid link starting with http:// or https://. 😕", reply_markup=await get_main_menu(user_id))
                logger.warning(f"Invalid backup link format by user {user_id}")
                return
            await db_instance.save_group_settings(user_id, "backup_link", backup_link)
            await message.reply(f"Backup link set! ✅\nLink: <code>{backup_link}</code>", reply_markup=await get_main_menu(user_id))
            await state.clear()
            logger.info(f"Backup link set for user {user_id}")
        except Exception as e:
            logger.error(f"Error processing backup link for user {user_id}: {e}")
            await message.reply("Failed to set backup link. Try again. 😕", reply_markup=await get_main_menu(user_id))
            await state.clear()

    @dp.callback_query(lambda c: c.data == "set_how_to_download")
    async def set_how_to_download(callback: types.CallbackQuery, state: FSMContext):
        user_id = callback.from_user.id
        logger.info(f"User {user_id} setting how to download")
        try:
            await state.set_state(BotStates.SET_HOW_TO_DOWNLOAD)
            await callback.message.edit_text(
                "Please send the 'How to Download' tutorial URL. 📖",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="Cancel ❌", callback_data="cancel_how_to_download")]
                ])
            )
            await callback.answer()
            logger.info(f"Prompted user {user_id} to set how to download")
        except Exception as e:
            logger.error(f"Error prompting how to download setup for user {user_id}: {e}")
            await callback.message.reply("Failed to initiate how to download setup. Try again. 😕", reply_markup=await get_main_menu(user_id))

    @dp.callback_query(lambda c: c.data == "cancel_how_to_download")
    async def cancel_how_to_download(callback: types.CallbackQuery, state: FSMContext):
        user_id = callback.from_user.id
        logger.info(f"User {user_id} canceled how to download setup")
        try:
            await state.clear()
            await callback.message.edit_text("How to Download setup canceled. Returning to main menu... 😕", reply_markup=await get_main_menu(user_id))
            logger.info(f"Canceled how to download setup for user {user_id}")
            await callback.answer()
        except Exception as e:
            logger.error(f"Error canceling how to download setup for user {user_id}: {e}")
            await callback.message.reply("Failed to cancel. Try again. 😕", reply_markup=await get_main_menu(user_id))

    @dp.message(StateFilter(BotStates.SET_HOW_TO_DOWNLOAD))
    async def process_how_to_download(message: types.Message, state: FSMContext):
        user_id = message.from_user.id
        logger.info(f"User {user_id} processing how to download")
        try:
            how_to_download = message.text.strip()
            if not how_to_download.startswith("http"):
                await message.reply("Invalid URL! Send a valid link starting with http:// or https://. 😕", reply_markup=await get_main_menu(user_id))
                logger.warning(f"Invalid how to download link format by user {user_id}")
                return
            await db_instance.save_group_settings(user_id, "how_to_download", how_to_download)
            await message.reply(f"How to Download link set! ✅\nLink: <code>{how_to_download}</code>", reply_markup=await get_main_menu(user_id))
            await state.clear()
            logger.info(f"How to download link set for user {user_id}")
        except Exception as e:
            logger.error(f"Error processing how to download for user {user_id}: {e}")
            await message.reply("Failed to set how to download link. Try again. 😕", reply_markup=await get_main_menu(user_id))
            await state.clear()

    @dp.callback_query(lambda c: c.data == "add_clone")
    async def add_clone(callback: types.CallbackQuery, state: FSMContext):
        user_id = callback.from_user.id
        logger.info(f"User {user_id} adding clone bot")
        try:
            existing_clone = await db_instance.get_clone_bot(user_id)
            if existing_clone:
                await callback.message.edit_text(
                    "You already have a clone bot! 🤖 Check 'My Clones' to manage it.",
                    reply_markup=await get_main_menu(user_id)
                )
                await callback.answer()
                logger.info(f"User {user_id} already has a clone bot")
                return
            await state.set_state(BotStates.SET_CLONE_TOKEN)
            await callback.message.edit_text(
                "Send the bot token for your clone bot. 🤖\nObtain a token via @BotFather.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="Cancel ❌", callback_data="cancel_clone")]
                ])
            )
            await callback.answer()
            logger.info(f"Prompted user {user_id} to add clone bot token")
        except Exception as e:
            logger.error(f"Error prompting clone bot setup for user {user_id}: {e}")
            await callback.message.reply("Failed to initiate clone bot setup. Try again. 😕", reply_markup=await get_main_menu(user_id))

    @dp.callback_query(lambda c: c.data == "cancel_clone")
    async def cancel_clone(callback: types.CallbackQuery, state: FSMContext):
        user_id = callback.from_user.id
        logger.info(f"User {user_id} canceled clone bot setup")
        try:
            await state.clear()
            await callback.message.edit_text("Clone bot setup canceled. Returning to main menu... 😕", reply_markup=await get_main_menu(user_id))
            logger.info(f"Canceled clone bot setup for user {user_id}")
            await callback.answer()
        except Exception as e:
            logger.error(f"Error canceling clone bot setup for user {user_id}: {e}")
            await callback.message.reply("Failed to cancel. Try again. 😕", reply_markup=await get_main_menu(user_id))

    @dp.message(StateFilter(BotStates.SET_CLONE_TOKEN))
    async def process_clone_token(message: types.Message, state: FSMContext):
        user_id = message.from_user.id
        logger.info(f"User {user_id} processing clone bot token")
        try:
            token = message.text.strip()
            if not token.count(":") == 1 or len(token) < 35:
                raise ValueError("Invalid token format")
            # Validate token by creating a temporary bot instance
            test_bot = Bot(token=token)
            bot_info = await test_bot.get_me()
            username = f"@{bot_info.username}" if bot_info.username else "Unknown"
            await db_instance.save_clone_bot(user_id, token, username)
            await message.reply(
                f"Clone bot {username} added successfully! ✅\nStart your clone bot with /start.",
                reply_markup=await get_main_menu(user_id)
            )
            await state.clear()
            logger.info(f"Clone bot {username} saved and validated for user {user_id}")
        except Exception as e:
            logger.error(f"Error adding clone bot for user {user_id}: {e}")
            await message.reply(f"Failed to add clone bot: {str(e)} 😕\nSend a valid token.", reply_markup=await get_main_menu(user_id))
            await state.clear()

    @dp.callback_query(lambda c: c.data == "my_clones")
    async def show_my_clones(callback: types.CallbackQuery):
        user_id = callback.from_user.id
        logger.info(f"User {user_id} viewing clone bots")
        try:
            clone_bot = await db_instance.get_clone_bot(user_id)
            new_markup = await get_main_menu(user_id)
            if clone_bot:
                new_text = f"Your Clone Bot: 🤖\nUsername: <code>{clone_bot['username']}</code>\nStart it with /start."
            else:
                new_text = "No clone bots created yet! 🚫\nUse 'Add Clone Bot' to create one."
            current_text = getattr(callback.message, 'text', '')
            if current_text != new_text:
                await callback.message.edit_text(new_text, reply_markup=new_markup)
            await callback.answer()
            logger.info(f"Displayed clone bots for user {user_id}")
        except Exception as e:
            logger.error(f"Error showing clone bots for user {user_id}: {e}")
            await callback.message.reply("Failed to fetch clone bots. Try again. 😕", reply_markup=await get_main_menu(user_id))

    @dp.callback_query(lambda c: c.data == "clone_search")
    async def clone_search(callback: types.CallbackQuery):
        user_id = callback.from_user.id
        logger.info(f"User {user_id} initiating clone search")
        try:
            await callback.message.edit_text(
                "Clone search is not implemented yet. 😕\nReturning to main menu...",
                reply_markup=await get_main_menu(user_id)
            )
            await callback.answer()
            logger.info(f"Clone search placeholder displayed for user {user_id}")
        except Exception as e:
            logger.error(f"Error in clone search for user {user_id}: {e}")
            await callback.message.reply("Failed to initiate clone search. Try again. 😕", reply_markup=await get_main_menu(user_id))
