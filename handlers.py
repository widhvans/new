from aiogram import Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import Command, StateFilter, BaseFilter
import asyncio
import logging
from database import Database
from shortener import Shortener

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

def get_main_menu():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📢 Add Post Channel", callback_data="add_post_channel"),
            InlineKeyboardButton(text="🗄️ Add Database Channel", callback_data="add_database_channel")
        ],
        [
            InlineKeyboardButton(text="🔗 Set Shortener", callback_data="set_shortener"),
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

def register_handlers(dp: Dispatcher, db: Database, shortener: Shortener):
    ADMINS = [123456789]  # Replace with actual admin IDs

    @dp.message(Command("start"))
    async def start_command(message: types.Message):
        logger.debug(f"User {message.from_user.id} initiated /start")
        welcome_msg = (
            "Welcome to your personal storage bot! 📦\n"
            "I can save your media, auto-post to channels, and more.\n"
            "Let's get started! 🚀"
        )
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Let's Begin! ▶️", callback_data="main_menu")]
        ])
        try:
            await message.reply(welcome_msg, reply_markup=keyboard)
            logger.info(f"Sent start message to user {message.from_user.id}")
        except Exception as e:
            logger.error(f"Failed to send start message to user {message.from_user.id}: {e}")

    @dp.callback_query(lambda c: c.data == "main_menu")
    async def show_main_menu(callback: types.CallbackQuery):
        logger.debug(f"User {callback.from_user.id} requested main menu")
        new_text = "Choose an option: 🛠️"
        current_text = getattr(callback.message, 'text', '')
        current_markup = getattr(callback.message, 'reply_markup', None)
        new_markup = get_main_menu()
        try:
            if current_text != new_text or current_markup != new_markup:
                await callback.message.edit_text(new_text, reply_markup=new_markup)
                logger.info(f"Displayed main menu for user {callback.from_user.id}")
            await callback.answer()
        except Exception as e:
            logger.error(f"Failed to show main menu for user {callback.from_user.id}: {e}")

    @dp.callback_query(lambda c: c.data == "add_post_channel")
    async def add_post_channel(callback: types.CallbackQuery, state: FSMContext):
        logger.debug(f"User {callback.from_user.id} adding post channel")
        try:
            await state.set_state(BotStates.SET_POST_CHANNEL)
            await callback.message.edit_text(
                "Please add me as an admin to your post channel and forward a message from that channel. 📢"
            )
            await callback.answer()
            logger.info(f"Prompted user {callback.from_user.id} to add post channel")
        except Exception as e:
            logger.error(f"Failed to prompt post channel setup for user {callback.from_user.id}: {e}")

    @dp.message(StateFilter(BotStates.SET_POST_CHANNEL))
    async def process_post_channel(message: types.Message, state: FSMContext):
        user_id = message.from_user.id
        logger.debug(f"User {user_id} processing post channel")
        try:
            if not message.forward_from_chat or message.forward_from_chat.type != "channel":
                await message.reply("Please forward a message from a channel. 🔄")
                logger.warning(f"User {user_id} sent invalid forward for post channel")
                return
            channel_id = message.forward_from_chat.id
            # Verify bot is admin
            bot_member = await message.bot.get_chat_member(channel_id, message.bot.id)
            if bot_member.status not in ["administrator", "creator"]:
                await message.reply("I must be an admin in the channel to save it. Please add me as an admin. 🚫")
                logger.warning(f"Bot not admin in channel {channel_id} for user {user_id}")
                return
            channels = await db.get_channels(user_id, "post")
            if len(channels) >= 5:
                await message.reply("Max 5 post channels allowed! 🚫")
                await state.clear()
                logger.warning(f"User {user_id} exceeded post channel limit")
                return
            await db.save_channel(user_id, "post", channel_id)
            await message.reply("Post channel connected! ✅ Add more or go back.", reply_markup=get_main_menu())
            await state.clear()
            logger.info(f"Post channel {channel_id} saved for user {user_id}")
        except Exception as e:
            logger.error(f"Error processing post channel for user {user_id}: {e}")
            await message.reply("Failed to save post channel. Please try again. 😕")
            await state.clear()

    @dp.callback_query(lambda c: c.data == "add_database_channel")
    async def add_database_channel(callback: types.CallbackQuery, state: FSMContext):
        logger.debug(f"User {callback.from_user.id} adding database channel")
        try:
            await state.set_state(BotStates.SET_DATABASE_CHANNEL)
            await callback.message.edit_text(
                "Please add me as an admin to your database channel and forward a message from that channel. 🗄️"
            )
            await callback.answer()
            logger.info(f"Prompted user {callback.from_user.id} to add database channel")
        except Exception as e:
            logger.error(f"Failed to prompt database channel setup for user {callback.from_user.id}: {e}")

    @dp.message(StateFilter(BotStates.SET_DATABASE_CHANNEL))
    async def process_database_channel(message: types.Message, state: FSMContext):
        user_id = message.from_user.id
        logger.debug(f"User {user_id} processing database channel")
        try:
            if not message.forward_from_chat or message.forward_from_chat.type != "channel":
                await message.reply("Please forward a message from a channel. 🔄")
                logger.warning(f"User {user_id} sent invalid forward for database channel")
                return
            channel_id = message.forward_from_chat.id
            # Verify bot is admin
            bot_member = await message.bot.get_chat_member(channel_id, message.bot.id)
            if bot_member.status not in ["administrator", "creator"]:
                await message.reply("I must be an admin in the channel to save it. Please add me as an admin. 🚫")
                logger.warning(f"Bot not admin in channel {channel_id} for user {user_id}")
                return
            channels = await db.get_channels(user_id, "database")
            if len(channels) >= 5:
                await message.reply("Max 5 database channels allowed! 🚫")
                await state.clear()
                logger.warning(f"User {user_id} exceeded database channel limit")
                return
            await db.save_channel(user_id, "database", channel_id)
            await message.reply("Database channel connected! ✅ Add more or go back.", reply_markup=get_main_menu())
            await state.clear()
            logger.info(f"Database channel {channel_id} saved for user {user_id}")
        except Exception as e:
            logger.error(f"Error processing database channel for user {user_id}: {e}")
            await message.reply("Failed to save database channel. Please try again. 😕")
            await state.clear()

    @dp.message(Command("shortlink"))
    async def shortlink_command(message: types.Message):
        user_id = message.from_user.id
        chat_type = message.chat.type
        grp_id = user_id if chat_type == "private" else message.chat.id
        title = "PM" if chat_type == "private" else message.chat.title
        logger.debug(f"User {user_id} setting shortlink for chat {grp_id}")

        try:
            if chat_type != "private":
                member = await message.bot.get_chat_member(grp_id, user_id)
                if member.status not in ["administrator", "creator"] and str(user_id) not in ADMINS:
                    await message.reply("<b>You don't have access to this command! 🚫</b>")
                    logger.warning(f"User {user_id} lacks permission for /shortlink in chat {grp_id}")
                    return

            _, shortlink_url, api = message.text.split(" ")
            reply = await message.reply("<b>Please wait... ⏳</b>")
            await db.save_shortener(grp_id, shortlink_url, api)
            await reply.edit_text(
                f"<b>Successfully added shortlink API for {title} ✅\n\nCurrent shortlink website: <code>{shortlink_url}</code>\nCurrent API: <code>{api}</code>.</b>"
            )
            logger.info(f"Shortlink set for chat {grp_id} by user {user_id}")
        except ValueError:
            await message.reply(
                f"<b>Hey {message.from_user.mention}, command incomplete 😕\n\nUse proper format!\n\n<code>/shortlink mdisk.link b6d97f6s96ds69d69d68d575d</code></b>"
            )
            logger.warning(f"Invalid /shortlink format by user {user_id}")
        except Exception as e:
            logger.error(f"Error setting shortlink for user {user_id}: {e}")
            await message.reply("Failed to set shortlink. Please try again. 😕")

    @dp.message(MediaFilter())
    async def handle_media(message: types.Message):
        user_id = message.from_user.id
        chat_id = message.chat.id
        logger.debug(f"User {user_id} sent media in chat {chat_id}")

        try:
            database_channels = await db.get_channels(user_id, "database")
            if not database_channels:
                logger.warning(f"No database channels configured for user {user_id}")
                await message.reply("No database channels set! Please add one via 'Add Database Channel'. 🚫")
                return
            if chat_id not in database_channels:
                logger.debug(f"Chat {chat_id} is not a database channel for user {user_id}")
                return

            # Verify bot is admin in database channel
            bot_member = await message.bot.get_chat_member(chat_id, message.bot.id)
            if bot_member.status not in ["administrator", "creator"]:
                logger.warning(f"Bot not admin in database channel {chat_id} for user {user_id}")
                await message.reply("I must be an admin in this database channel to process media. 🚫")
                return

            file_id = None
            file_name = None
            media_type = None
            file_size = None
            if message.photo:
                file_id = message.photo[-1].file_id
                media_type = "photo"
                file_name = f"photo_{message.message_id}.jpg"
                file_size = message.photo[-1].file_size or "Unknown"
            elif message.video:
                file_id = message.video.file_id
                media_type = "video"
                file_name = message.video.file_name or f"video_{message.message_id}.mp4"
                file_size = message.video.file_size or "Unknown"
            elif message.document:
                file_id = message.document.file_id
                media_type = "document"
                file_name = message.document.file_name or f"doc_{message.message_id}"
                file_size = message.document.file_size or "Unknown"

            if file_id:
                raw_link = f"telegram://file/{file_id}"
                await db.save_media(user_id, media_type, file_id, file_name, raw_link, file_size)
                logger.info(f"Saved media {file_name} for user {user_id} in chat {chat_id}")
                # Schedule posting after delay
                asyncio.create_task(post_media_with_delay(dp.bot, user_id, file_name, raw_link, chat_id))
                await message.reply("Media saved! Will post to your channels shortly. ✅")
            else:
                logger.warning(f"No valid file ID found in media message from user {user_id}")
                await message.reply("Invalid media file. Please try again. 😕")
        except Exception as e:
            logger.error(f"Error handling media for user {user_id} in chat {chat_id}: {e}")
            await message.reply("Failed to process media. Please try again. 😕")

    async def post_media_with_delay(bot, user_id, file_name, raw_link, chat_id):
        try:
            await asyncio.sleep(20)  # Delay to ensure file is processed
            await post_media(bot, user_id, file_name, raw_link, chat_id)
        except Exception as e:
            logger.error(f"Error in delayed post_media for user {user_id}: {e}")

    async def post_media(bot, user_id, file_name, raw_link, chat_id):
        logger.debug(f"Posting media {file_name} for user {user_id} from chat {chat_id}")
        try:
            shortener_settings = await db.get_shortener(chat_id)
            if not shortener_settings:
                logger.warning(f"No shortener settings for chat {chat_id}, user {user_id}")
                return
            short_link = await shortener.get_shortlink(raw_link, chat_id)
            post_channels = await db.get_channels(user_id, "post")
            if not post_channels:
                logger.warning(f"No post channels configured for user {user_id}")
                return

            backup_link = (await db.get_settings(user_id)).get("backup_link", "")
            how_to_download = (await db.get_settings(user_id)).get("how_to_download", "")
            poster_url = await fetch_poster(file_name)

            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Download 📥", url=short_link)]
            ])
            if backup_link:
                keyboard.inline_keyboard.append([InlineKeyboardButton(text="Backup Link 🔄", url=backup_link)])
            if how_to_download:
                keyboard.inline_keyboard.append([InlineKeyboardButton(text="How to Download ❓", url=how_to_download)])

            for channel_id in post_channels:
                try:
                    # Verify bot is admin in post channel
                    bot_member = await bot.get_chat_member(channel_id, bot.id)
                    if bot_member.status not in ["administrator", "creator"]:
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
        logger.debug(f"Fetching poster for file {file_name}")
        try:
            return None  # Implement Cinemagoer logic
        except Exception as e:
            logger.error(f"Error fetching poster for file {file_name}: {e}")
            return None

    @dp.callback_query(lambda c: c.data == "total_files")
    async def show_total_files(callback: types.CallbackQuery):
        user_id = callback.from_user.id
        logger.debug(f"User {user_id} checking total files")
        try:
            media_files = await db.get_user_media(user_id)
            new_text = f"Total files: {len(media_files)} 📊"
            current_text = getattr(callback.message, 'text', '')
            current_markup = getattr(callback.message, 'reply_markup', None)
            new_markup = get_main_menu()
            if current_text != new_text or current_markup != new_markup:
                await callback.message.edit_text(new_text, reply_markup=new_markup)
            await callback.answer()
            logger.info(f"Displayed total files ({len(media_files)}) for user {user_id}")
        except Exception as e:
            logger.error(f"Error showing total files for user {user_id}: {e}")
            await callback.message.reply("Failed to fetch total files. Please try again. 😕")

    @dp.message(Command("broadcast"))
    async def broadcast_command(message: types.Message):
        user_id = message.from_user.id
        logger.debug(f"User {user_id} attempting broadcast")
        try:
            if user_id not in ADMINS:
                logger.warning(f"User {user_id} not authorized for broadcast")
                return
            await message.reply("Send the broadcast message. 📢")
            logger.info(f"Broadcast initiated by admin {user_id}")
        except Exception as e:
            logger.error(f"Error in broadcast command for user {user_id}: {e}")

    @dp.message(Command("stats"))
    async def stats_command(message: types.Message):
        user_id = message.from_user.id
        logger.debug(f"User {user_id} requesting stats")
        try:
            if user_id not in ADMINS:
                logger.warning(f"User {user_id} not authorized for stats")
                return
            total_users = await db.db.users.count_documents({})
            total_db_owners = await db.db.channels.count_documents({"channel_type": "database"})
            await message.reply(f"Users: {total_users}\nDatabase Owners: {total_db_owners} 📈")
            logger.info(f"Displayed stats for admin {user_id}")
        except Exception as e:
            logger.error(f"Error in stats command for user {user_id}: {e}")
            await message.reply("Failed to fetch stats. Please try again. 😕")

    @dp.callback_query(lambda c: c.data == "set_shortener")
    async def set_shortener(callback: types.CallbackQuery, state: FSMContext):
        logger.debug(f"User {callback.from_user.id} setting shortener")
        try:
            await state.set_state(BotStates.SET_SHORTENER)
            await callback.message.edit_text(
                "Send the shortener details in format: <code>shortlink mdisk.link your_api_key</code> 🔗"
            )
            await callback.answer()
            logger.info(f"Prompted user {callback.from_user.id} to set shortener")
        except Exception as e:
            logger.error(f"Error prompting shortener setup for user {callback.from_user.id}: {e}")

    @dp.message(StateFilter(BotStates.SET_SHORTENER))
    async def process_shortener(message: types.Message, state: FSMContext):
        user_id = message.from_user.id
        logger.debug(f"User {user_id} processing shortener")
        try:
            _, shortlink_url, api = message.text.split(" ")
            await db.save_shortener(user_id, shortlink_url, api)
            await message.reply(
                f"Shortener set! ✅\nWebsite: <code>{shortlink_url}</code>\nAPI: <code>{api}</code>",
                reply_markup=get_main_menu()
            )
            await state.clear()
            logger.info(f"Shortener set for user {user_id}")
        except ValueError:
            await message.reply(
                "Invalid format! Use: <code>shortlink mdisk.link your_api_key</code> 😕"
            )
            logger.warning(f"Invalid shortener format by user {user_id}")
        except Exception as e:
            logger.error(f"Error processing shortener for user {user_id}: {e}")
            await message.reply("Failed to set shortener. Please try again. 😕")
            await state.clear()

    @dp.callback_query(lambda c: c.data == "see_shortener")
    async def see_shortener(callback: types.CallbackQuery):
        user_id = callback.from_user.id
        logger.debug(f"User {user_id} viewing shortener")
        try:
            shortener = await db.get_shortener(user_id)
            new_markup = get_main_menu()
            if shortener:
                new_text = f"Current Shortener: 👀\nWebsite: <code>{shortener['url']}</code>\nAPI: <code>{shortener['api']}</code>"
            else:
                new_text = "No shortener set! 🚫"
            current_text = getattr(callback.message, 'text', '')
            current_markup = getattr(callback.message, 'reply_markup', None)
            if current_text != new_text or current_markup != new_markup:
                await callback.message.edit_text(new_text, reply_markup=new_markup)
            await callback.answer()
            logger.info(f"Displayed shortener for user {user_id}")
        except Exception as e:
            logger.error(f"Error showing shortener for user {user_id}: {e}")
            await callback.message.reply("Failed to fetch shortener. Please try again. 😕")

    @dp.callback_query(lambda c: c.data == "set_backup_link")
    async def set_backup_link(callback: types.CallbackQuery, state: FSMContext):
        logger.debug(f"User {callback.from_user.id} setting backup link")
        try:
            await state.set_state(BotStates.SET_BACKUP_LINK)
            await callback.message.edit_text(
                "Please send the backup link URL. 🔄"
            )
            await callback.answer()
            logger.info(f"Prompted user {callback.from_user.id} to set backup link")
        except Exception as e:
            logger.error(f"Error prompting backup link setup for user {callback.from_user.id}: {e}")

    @dp.message(StateFilter(BotStates.SET_BACKUP_LINK))
    async def process_backup_link(message: types.Message, state: FSMContext):
        user_id = message.from_user.id
        logger.debug(f"User {user_id} processing backup link")
        try:
            backup_link = message.text.strip()
            if not backup_link.startswith("http"):
                await message.reply("Invalid URL! Please send a valid link starting with http:// or https://. 😕")
                logger.warning(f"Invalid backup link format by user {user_id}")
                return
            await db.save_group_settings(user_id, "backup_link", backup_link)
            await message.reply(f"Backup link set! ✅\nLink: <code>{backup_link}</code>", reply_markup=get_main_menu())
            await state.clear()
            logger.info(f"Backup link set for user {user_id}")
        except Exception as e:
            logger.error(f"Error processing backup link for user {user_id}: {e}")
            await message.reply("Failed to set backup link. Please try again. 😕")
            await state.clear()

    @dp.callback_query(lambda c: c.data == "set_how_to_download")
    async def set_how_to_download(callback: types.CallbackQuery, state: FSMContext):
        logger.debug(f"User {callback.from_user.id} setting how to download")
        try:
            await state.set_state(BotStates.SET_HOW_TO_DOWNLOAD)
            await callback.message.edit_text(
                "Please send the 'How to Download' tutorial URL. 📖"
            )
            await callback.answer()
            logger.info(f"Prompted user {callback.from_user.id} to set how to download")
        except Exception as e:
            logger.error(f"Error prompting how to download setup for user {callback.from_user.id}: {e}")

    @dp.message(StateFilter(BotStates.SET_HOW_TO_DOWNLOAD))
    async def process_how_to_download(message: types.Message, state: FSMContext):
        user_id = message.from_user.id
        logger.debug(f"User {user_id} processing how to download")
        try:
            how_to_download = message.text.strip()
            if not how_to_download.startswith("http"):
                await message.reply("Invalid URL! Please send a valid link starting with http:// or https://. 😕")
                logger.warning(f"Invalid how to download link format by user {user_id}")
                return
            await db.save_group_settings(user_id, "how_to_download", how_to_download)
            await message.reply(f"How to Download link set! ✅\nLink: <code>{how_to_download}</code>", reply_markup=get_main_menu())
            await state.clear()
            logger.info(f"How to download link set for user {user_id}")
        except Exception as e:
            logger.error(f"Error processing how to download for user {user_id}: {e}")
            await message.reply("Failed to set how to download link. Please try again. 😕")
            await state.clear()

    @dp.callback_query(lambda c: c.data == "add_clone")
    async def add_clone(callback: types.CallbackQuery, state: FSMContext):
        user_id = callback.from_user.id
        logger.debug(f"User {user_id} adding clone bot")
        try:
            existing_clone = await db.get_clone_bot(user_id)
            if existing_clone:
                await callback.message.edit_text(
                    "You already have a clone bot! 🤖 Check 'My Clones' to manage it.",
                    reply_markup=get_main_menu()
                )
                await callback.answer()
                logger.info(f"User {user_id} already has a clone bot")
                return
            await state.set_state(BotStates.SET_CLONE_TOKEN)
            await callback.message.edit_text(
                "Please send the bot token for your clone bot. 🤖\nObtain a token by creating a new bot via @BotFather."
            )
            await callback.answer()
            logger.info(f"Prompted user {user_id} to add clone bot token")
        except Exception as e:
            logger.error(f"Error prompting clone bot setup for user {user_id}: {e}")

    @dp.message(StateFilter(BotStates.SET_CLONE_TOKEN))
    async def process_clone_token(message: types.Message, state: FSMContext):
        user_id = message.from_user.id
        logger.debug(f"User {user_id} processing clone bot token")
        try:
            token = message.text.strip()
            if not token.count(":") == 1 or len(token) < 35:
                raise ValueError("Invalid token format")
            await db.save_clone_bot(user_id, token)
            await message.reply(
                "Clone bot added successfully! ✅\nStart your clone bot with /start to use it.",
                reply_markup=get_main_menu()
            )
            await state.clear()
            logger.info(f"Clone bot token saved for user {user_id}")
        except Exception as e:
            logger.error(f"Error adding clone bot for user {user_id}: {e}")
            await message.reply(f"Failed to add clone bot: {str(e)} 😕\nPlease send a valid token.")
            await state.clear()

    @dp.callback_query(lambda c: c.data == "my_clones")
    async def show_my_clones(callback: types.CallbackQuery):
        user_id = callback.from_user.id
        logger.debug(f"User {user_id} viewing clone bots")
        try:
            clone_bot = await db.get_clone_bot(user_id)
            new_markup = get_main_menu()
            if clone_bot:
                new_text = f"Your Clone Bot: 🤖\nToken: <code>{clone_bot['token']}</code>\nStart it with /start in the bot."
            else:
                new_text = "No clone bots created yet! 🚫\nUse 'Add Clone Bot' to create one."
            current_text = getattr(callback.message, 'text', '')
            current_markup = getattr(callback.message, 'reply_markup', None)
            if current_text != new_text or current_markup != new_markup:
                await callback.message.edit_text(new_text, reply_markup=new_markup)
            await callback.answer()
            logger.info(f"Displayed clone bots for user {user_id}")
        except Exception as e:
            logger.error(f"Error showing clone bots for user {user_id}: {e}")
            await callback.message.reply("Failed to fetch clone bots. Please try again. 😕")
