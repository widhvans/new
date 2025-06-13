from aiogram import Dispatcher, types, Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import Command, StateFilter, BaseFilter
import asyncio
import logging
from database import Database
from shortener import Shortener
from channels import ChannelManager
from media import MediaManager
from search import SearchManager
from admin import AdminManager
from config import BOT_USERNAME, logger, ADMIN_IDS

class BotStates(StatesGroup):
    SET_POST_CHANNEL = State()
    SET_DATABASE_CHANNEL = State()
    SET_SHORTENER = State()
    SET_BACKUP_LINK = State()
    SET_HOW_TO_DOWNLOAD = State()
    SET_CLONE_TOKEN = State()
    SET_FSUB = State()
    BROADCAST = State()
    SEARCH = State()

class MediaFilter(BaseFilter):
    async def __call__(self, message: types.Message) -> bool:
        return message.content_type in [types.ContentType.PHOTO, types.ContentType.VIDEO, types.ContentType.DOCUMENT]

async def check_subscription(bot: Bot, user_id: int, channel_id: int):
    try:
        if not channel_id:
            return True
        member = await bot.get_chat_member(channel_id, user_id)
        return member.status in ["member", "administrator", "creator"]
    except Exception as e:
        logger.error(f"Error checking subscription for user {user_id} in channel {channel_id}: {e}")
        return False

def register_handlers(dp: Dispatcher, db: Database, shortener: Shortener, bot: Bot):
    channel_manager = ChannelManager(db)
    media_manager = MediaManager(db, shortener)
    search_manager = SearchManager(db, shortener)
    admin_manager = AdminManager(db)

    @dp.message(Command("start"))
    async def start_command(message: types.Message, state: FSMContext):
        user_id = message.from_user.id
        logger.info(f"User {user_id} initiated /start")
        await state.clear()
        await db.save_user(user_id)
        settings = await db.get_settings(user_id)
        fsub_channel_id = settings.get("fsub_channel_id", None)
        if not await check_subscription(bot, user_id, fsub_channel_id):
            channel = await bot.get_chat(fsub_channel_id)
            invite_link = await channel.export_invite_link()
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Join Channel 📢", url=invite_link)],
                [InlineKeyboardButton(text="Check Subscription ✅", callback_data="check_subscription")]
            ])
            await message.reply(
                f"Please join our channel to use the bot! 😊\nAfter joining, click 'Check Subscription'.",
                reply_markup=keyboard,
                parse_mode="HTML"
            )
            logger.info(f"User {user_id} prompted to join FSub channel {fsub_channel_id}")
            return
        welcome_msg = (
            f"Welcome to {BOT_USERNAME}! 📦\n\n"
            "I'm your personal storage bot. You can:\n"
            "- Save media files and get links\n"
            "- Auto-post to your channels\n"
            "- Search files with a clone bot\n"
            "- Use any shortener\n"
            "Click 'Let's Begin!' to start! 🚀"
        )
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Let's Begin! ▶️", callback_data="main_menu")]
        ])
        try:
            await message.reply(welcome_msg, reply_markup=keyboard, parse_mode="HTML")
            logger.info(f"Sent start message to user {user_id}")
        except Exception as e:
            logger.error(f"Failed to send start message to user {user_id}: {e}")

    @dp.callback_query(lambda c: c.data == "check_subscription")
    async def check_subscription_callback(callback: types.CallbackQuery, state: FSMContext):
        user_id = callback.from_user.id
        logger.info(f"User {user_id} checking subscription")
        settings = await db.get_settings(user_id)
        fsub_channel_id = settings.get("fsub_channel_id", None)
        if await check_subscription(bot, user_id, fsub_channel_id):
            await state.clear()
            welcome_msg = (
                f"Welcome to {BOT_USERNAME}! 📦\n\n"
                "I'm your personal storage bot. You can:\n"
                "- Save media files and get links\n"
                "- Auto-post to your channels\n"
                "- Search files with a clone bot\n"
                "- Use any shortener\n"
                "Click 'Let's Begin!' to start! 🚀"
            )
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Let's Begin! ▶️", callback_data="main_menu")]
            ])
            await callback.message.edit_text(welcome_msg, reply_markup=keyboard, parse_mode="HTML")
            logger.info(f"User {user_id} passed subscription check")
        else:
            await callback.answer("You haven’t joined the channel yet! Please join and try again.", show_alert=True)
            logger.info(f"User {user_id} failed subscription check")

    @dp.callback_query(lambda c: c.data == "main_menu")
    async def show_main_menu(callback: types.CallbackQuery, state: FSMContext):
        user_id = callback.from_user.id
        logger.info(f"User {user_id} requested main menu")
        await state.clear()
        try:
            new_text = "Choose an option: 🛠️"
            new_markup = await channel_manager.get_main_menu(user_id)
            if callback.message.text != new_text or callback.message.reply_markup != new_markup:
                await callback.message.edit_text(new_text, reply_markup=new_markup, parse_mode="HTML")
            logger.info(f"Displayed main menu for user {user_id}")
            await callback.answer()
        except Exception as e:
            logger.error(f"Failed to show main menu for user {user_id}: {e}")
            await callback.message.reply("Failed to show menu. Try again. 😕", reply_markup=await channel_manager.get_main_menu(user_id))

    @dp.callback_query(lambda c: c.data == "add_post_channel")
    async def add_post_channel(callback: types.CallbackQuery, state: FSMContext):
        user_id = callback.from_user.id
        logger.info(f"User {user_id} adding post channel")
        try:
            channels = await db.get_channels(user_id, "post")
            if len(channels) >= 5:
                await callback.message.edit_text("Max 5 post channels allowed! 🚫", reply_markup=await channel_manager.get_main_menu(user_id))
                logger.warning(f"User {user_id} exceeded post channel limit")
                await callback.answer()
                return
            await state.set_state(BotStates.SET_POST_CHANNEL)
            await callback.message.edit_text(
                "Make me an admin in your post channel (public or private), then send the channel ID (e.g., -100123456789). 📢",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="Cancel ❌", callback_data="cancel_add_channel")]
                ])
            )
            logger.info(f"Prompted user {user_id} to add post channel")
            await callback.answer()
        except Exception as e:
            logger.error(f"Failed to prompt post channel setup for user {user_id}: {e}")
            await callback.message.reply("Failed to initiate post channel setup. Try again. 😕", reply_markup=await channel_manager.get_main_menu(user_id))
            await state.clear()

    @dp.callback_query(lambda c: c.data == "add_database_channel")
    async def add_database_channel(callback: types.CallbackQuery, state: FSMContext):
        user_id = callback.from_user.id
        logger.info(f"User {user_id} adding database channel")
        try:
            channels = await db.get_channels(user_id, "database")
            if len(channels) >= 5:
                await callback.message.edit_text("Max 5 database channels allowed! 🚫", reply_markup=await channel_manager.get_main_menu(user_id))
                logger.warning(f"User {user_id} exceeded database channel limit")
                await callback.answer()
                return
            await state.set_state(BotStates.SET_DATABASE_CHANNEL)
            await callback.message.edit_text(
                "Make me an admin in your database channel (public or private), then send the channel ID (e.g., -100123456789). 🗄️",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="Cancel ❌", callback_data="cancel_add_channel")]
                ])
            )
            logger.info(f"Prompted user {user_id} to add database channel")
            await callback.answer()
        except Exception as e:
            logger.error(f"Failed to prompt database channel setup for user {user_id}: {e}")
            await callback.message.reply("Failed to initiate database channel setup. Try again. 😕", reply_markup=await channel_manager.get_main_menu(user_id))
            await state.clear()

    @dp.callback_query(lambda c: c.data == "cancel_add_channel")
    async def cancel_add_channel(callback: types.CallbackQuery, state: FSMContext):
        user_id = callback.from_user.id
        logger.info(f"User {user_id} canceled channel addition")
        try:
            await state.clear()
            await callback.message.edit_text("Channel addition canceled. Returning to main menu... 😕", reply_markup=await channel_manager.get_main_menu(user_id))
            logger.info(f"Canceled channel addition for user {user_id}")
            await callback.answer()
        except Exception as e:
            logger.error(f"Error canceling channel addition for user {user_id}: {e}")
            await callback.message.reply("Failed to cancel. Try again. 😕", reply_markup=await channel_manager.get_main_menu(user_id))

    @dp.message(StateFilter(BotStates.SET_POST_CHANNEL, BotStates.SET_DATABASE_CHANNEL))
    async def process_channel_id(message: types.Message, state: FSMContext):
        user_id = message.from_user.id
        logger.info(f"User {user_id} sent channel ID: {message.text}")
        try:
            channel_id = int(message.text.strip())
            if not str(channel_id).startswith("-100"):
                await message.reply("Invalid channel ID format. Use format like -100123456789. 😕", reply_markup=await channel_manager.get_main_menu(user_id))
                logger.warning(f"Invalid channel ID format sent by user {user_id}: {message.text}")
                return
            user_state = await state.get_state()
            channel_type = "post" if user_state == BotStates.SET_POST_CHANNEL.state else "database"
            await channel_manager.connect_channel(bot, user_id, channel_id, channel_type, state)
            logger.info(f"Processed channel ID {channel_id} for user {user_id}, channel_type={channel_type}")
        except ValueError:
            await message.reply("Invalid channel ID. Please send a numeric ID like -100123456789. 😕", reply_markup=await channel_manager.get_main_menu(user_id))
            logger.warning(f"Non-numeric channel ID sent by user {user_id}: {message.text}")
        except Exception as e:
            logger.error(f"Error processing channel ID for user {user_id}: {e}")
            await message.reply("Failed to process channel ID. Try again. 😕", reply_markup=await channel_manager.get_main_menu(user_id))

    @dp.callback_query(lambda c: c.data == "see_post_channels")
    async def see_post_channels(callback: types.CallbackQuery):
        user_id = callback.from_user.id
        logger.info(f"User {user_id} viewing post channels")
        try:
            channels = await db.get_channels(user_id, "post")
            if not channels:
                new_text = "No post channels connected! 🚫"
                if callback.message.text != new_text:
                    await callback.message.edit_text(new_text, reply_markup=await channel_manager.get_main_menu(user_id))
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
            if callback.message.text != new_text or callback.message.reply_markup != keyboard:
                await callback.message.edit_text(new_text, reply_markup=keyboard)
            logger.info(f"Displayed {len(channels)} post channels for user {user_id}")
            await callback.answer()
        except Exception as e:
            logger.error(f"Error showing post channels for user {user_id}: {e}")
            await callback.message.reply("Failed to fetch post channels. Try again. 😕", reply_markup=await channel_manager.get_main_menu(user_id))

    @dp.callback_query(lambda c: c.data == "see_database_channels")
    async def see_database_channels(callback: types.CallbackQuery):
        user_id = callback.from_user.id
        logger.info(f"User {user_id} viewing database channels")
        try:
            channels = await db.get_channels(user_id, "database")
            if not channels:
                new_text = "No database channels connected! 🚫"
                if callback.message.text != new_text:
                    await callback.message.edit_text(new_text, reply_markup=await channel_manager.get_main_menu(user_id))
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
            if callback.message.text != new_text or callback.message.reply_markup != keyboard:
                await callback.message.edit_text(new_text, reply_markup=keyboard)
            logger.info(f"Displayed {len(channels)} database channels for user {user_id}")
            await callback.answer()
        except Exception as e:
            logger.error(f"Error showing database channels for user {user_id}: {e}")
            await callback.message.reply("Failed to fetch database channels. Try again. 😕", reply_markup=await channel_manager.get_main_menu(user_id))

    @dp.callback_query(lambda c: c.data.startswith("delete_post_"))
    async def delete_post_channel(callback: types.CallbackQuery):
        user_id = callback.from_user.id
        logger.info(f"User {user_id} deleting post channel")
        try:
            channel_id = int(callback.data.split("_")[2])
            channels = await db.get_channels(user_id, "post")
            if channel_id not in channels:
                await callback.message.edit_text("Channel not found! 🚫", reply_markup=await channel_manager.get_main_menu(user_id))
                logger.warning(f"Post channel {channel_id} not found for user {user_id}")
                await callback.answer()
                return
            await db.db.channels.update_one(
                {"user_id": user_id},
                {"$pull": {"post_channel_ids": channel_id}}
            )
            channel = await bot.get_chat(channel_id)
            channel_name = channel.title or "Unnamed Channel"
            await callback.message.edit_text(f"Post channel {channel_name} deleted! ✅", reply_markup=await channel_manager.get_main_menu(user_id))
            logger.info(f"Deleted post channel {channel_id} for user {user_id}")
            await callback.answer()
        except Exception as e:
            logger.error(f"Error deleting post channel for user {user_id}: {e}")
            await callback.message.reply("Failed to delete post channel. Try again. 😕", reply_markup=await channel_manager.get_main_menu(user_id))

    @dp.callback_query(lambda c: c.data.startswith("delete_db_"))
    async def delete_database_channel(callback: types.CallbackQuery):
        user_id = callback.from_user.id
        logger.info(f"User {user_id} deleting database channel")
        try:
            channel_id = int(callback.data.split("_")[2])
            channels = await db.get_channels(user_id, "database")
            if channel_id not in channels:
                await callback.message.edit_text("Channel not found! 🚫", reply_markup=await channel_manager.get_main_menu(user_id))
                logger.warning(f"Database channel {channel_id} not found for user {user_id}")
                await callback.answer()
                return
            await db.db.channels.update_one(
                {"user_id": user_id},
                {"$pull": {"database_channel_ids": channel_id}}
            )
            channel = await bot.get_chat(channel_id)
            channel_name = channel.title or "Unnamed Channel"
            await callback.message.edit_text(f"Database channel {channel_name} deleted! ✅", reply_markup=await channel_manager.get_main_menu(user_id))
            logger.info(f"Deleted database channel {channel_id} for user {user_id}")
            await callback.answer()
        except Exception as e:
            logger.error(f"Error deleting database channel for user {user_id}: {e}")
            await callback.message.reply("Failed to delete database channel. Try again. 😕", reply_markup=await channel_manager.get_main_menu(user_id))

    @dp.message(Command("shortlink"))
    async def shortlink_command(message: types.Message):
        user_id = message.from_user.id
        chat_type = message.chat.type
        grp_id = user_id if chat_type == "private" else message.chat.id
        title = "PM" if chat_type == "private" else message.chat.title
        logger.info(f"User {user_id} setting shortlink for chat {grp_id}")
        try:
            if chat_type != "private":
                member = await bot.get_chat_member(grp_id, user_id)
                if member.status not in ["administrator", "creator"] and user_id not in ADMIN_IDS:
                    await message.reply("<b>You don't have access to this command! 🚫</b>", reply_markup=await channel_manager.get_main_menu(user_id), parse_mode="HTML")
                    logger.warning(f"User {user_id} lacks permission for /shortlink in chat {grp_id}")
                    return
            _, shortlink_url, api = message.text.split(" ")
            reply = await message.reply("<b>Please wait... ⏳</b>", parse_mode="HTML")
            await db.save_shortener(user_id, shortlink_url, api)
            test_link = await shortener.get_shortlink(db, "https://example.com", user_id)
            test_status = f"Test Link: <code>{test_link}</code>\n" if test_link and test_link.startswith("http") else "Test Link: Failed to generate, check API settings.\n"
            await reply.edit_text(
                f"<b>Successfully added shortlink API for {title} ✅</b>\n\nCurrent shortlink website: <code>{shortlink_url}</code>\nCurrent API: <code>{api}</code>\n{test_status}",
                reply_markup=await channel_manager.get_main_menu(user_id),
                parse_mode="HTML"
            )
            logger.info(f"Shortlink set for user {user_id}")
        except ValueError:
            await message.reply(
                f"<b>Hey {message.from_user.mention}, command incomplete 😕</b>\n\nUse proper format!\n\n<code>/shortlink mdisk.link b6d97f6s96ds69d69d68d575d</code>",
                reply_markup=await channel_manager.get_main_menu(user_id),
                parse_mode="HTML"
            )
            logger.warning(f"Invalid /shortlink format by user {user_id}")
        except Exception as e:
            logger.error(f"Error setting shortlink for user {user_id}: {e}")
            await message.reply("Failed to set shortlink. Try again. 😕", reply_markup=await channel_manager.get_main_menu(user_id))

    @dp.message(MediaFilter())
    async def handle_media(message: types.Message):
        user_id = message.from_user.id
        chat_id = message.chat.id
        logger.info(f"User {user_id} sent media in chat {chat_id}")
        await media_manager.index_media(bot, user_id, chat_id, message)

    @dp.callback_query(lambda c: c.data == "total_files")
    async def show_total_files(callback: types.CallbackQuery):
        user_id = callback.from_user.id
        logger.info(f"User {user_id} checking total files")
        try:
            media_files = await db.get_user_media(user_id)
            new_text = f"Total files: {len(media_files)} 📊"
            if callback.message.text != new_text:
                await callback.message.edit_text(new_text, reply_markup=await channel_manager.get_main_menu(user_id))
            logger.info(f"Displayed total files ({len(media_files)}) for user {user_id}")
            await callback.answer()
        except Exception as e:
            logger.error(f"Error showing total files for user {user_id}: {e}")
            await callback.message.reply("Failed to fetch total files. Try again. 😕", reply_markup=await channel_manager.get_main_menu(user_id))

    @dp.message(Command("broadcast"))
    async def broadcast_command(message: types.Message, state: FSMContext):
        user_id = message.from_user.id
        logger.info(f"User {user_id} attempting broadcast")
        if user_id not in ADMIN_IDS:
            await message.reply("You’re not authorized to use this command! 🚫")
            logger.warning(f"Unauthorized broadcast attempt by user {user_id}")
            return
        await state.set_state(BotStates.BROADCAST)
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Users 👥", callback_data="broadcast_users"),
             InlineKeyboardButton(text="Database Owners 🗄️", callback_data="broadcast_database_owners")],
            [InlineKeyboardButton(text="Both 🌐", callback_data="broadcast_both"),
             InlineKeyboardButton(text="Cancel ❌", callback_data="cancel_broadcast")]
        ])
        await message.reply("Select broadcast target: 📢", reply_markup=keyboard)
        logger.info(f"Broadcast initiated by admin {user_id}")

    @dp.callback_query(lambda c: c.data.startswith("broadcast_"))
    async def select_broadcast_target(callback: types.CallbackQuery, state: FSMContext):
        user_id = callback.from_user.id
        target = callback.data.split("_")[1]
        logger.info(f"User {user_id} selected broadcast target: {target}")
        await state.update_data(broadcast_target=target)
        await callback.message.edit_text("Send the broadcast message (text, photo, video, etc.). 📢")
        await callback.answer()

    @dp.message(StateFilter(BotStates.BROADCAST))
    async def process_broadcast_message(message: types.Message, state: FSMContext):
        user_id = message.from_user.id
        data = await state.get_data()
        target = data.get("broadcast_target")
        if not target:
            await message.reply("Broadcast canceled. 😕")
            await state.clear()
            return
        await admin_manager.broadcast(bot, user_id, message, target)
        await state.clear()

    @dp.callback_query(lambda c: c.data == "cancel_broadcast")
    async def cancel_broadcast(callback: types.CallbackQuery, state: FSMContext):
        user_id = callback.from_user.id
        logger.info(f"User {user_id} canceled broadcast")
        await state.clear()
        await callback.message.edit_text("Broadcast canceled. 😕", reply_markup=await channel_manager.get_main_menu(user_id))
        await callback.answer()

    @dp.message(Command("stats"))
    async def stats_command(message: types.Message):
        user_id = message.from_user.id
        logger.info(f"User {user_id} requesting stats")
        await admin_manager.stats(bot, user_id, message)

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
            await callback.message.reply("Failed to initiate shortener setup. Try again. 😕", reply_markup=await channel_manager.get_main_menu(user_id))

    @dp.callback_query(lambda c: c.data == "cancel_shortener")
    async def cancel_shortener(callback: types.CallbackQuery, state: FSMContext):
        user_id = callback.from_user.id
        logger.info(f"User {user_id} canceled shortener setup")
        try:
            await state.clear()
            await callback.message.edit_text("Shortener setup canceled. Returning to main menu... 😕", reply_markup=await channel_manager.get_main_menu(user_id))
            logger.info(f"Canceled shortener setup for user {user_id}")
            await callback.answer()
        except Exception as e:
            logger.error(f"Error canceling shortener setup for user {user_id}: {e}")
            await callback.message.reply("Failed to cancel. Try again. 😕", reply_markup=await channel_manager.get_main_menu(user_id))

    @dp.message(StateFilter(BotStates.SET_SHORTENER))
    async def process_shortener(message: types.Message, state: FSMContext):
        user_id = message.from_user.id
        logger.info(f"User {user_id} processing shortener")
        try:
            _, shortlink_url, api = message.text.split(" ")
            await db.save_shortener(user_id, shortlink_url, api)
            test_link = await shortener.get_shortlink(db, "https://example.com", user_id)
            test_status = f"Test Link: <code>{test_link}</code>\n" if test_link and test_link.startswith("http") else "Test Link: Failed to generate, check API settings.\n"
            await message.reply(
                f"Shortener set! ✅\nWebsite: <code>{shortlink_url}</code>\nAPI: <code>{api}</code>\n{test_status}",
                reply_markup=await channel_manager.get_main_menu(user_id),
                parse_mode="HTML"
            )
            await state.clear()
            logger.info(f"Shortener set for user {user_id}")
        except ValueError:
            await message.reply(
                "Invalid format! Use: <code>shortlink mdisk.link your_api_key</code> 😕",
                reply_markup=await channel_manager.get_main_menu(user_id)
            )
            logger.warning(f"Invalid shortener format by user {user_id}")
        except Exception as e:
            logger.error(f"Error processing shortener for user {user_id}: {e}")
            await message.reply("Failed to set shortener. Try again. 😕", reply_markup=await channel_manager.get_main_menu(user_id))
            await state.clear()

    @dp.callback_query(lambda c: c.data == "see_shortener")
    async def see_shortener(callback: types.CallbackQuery):
        user_id = callback.from_user.id
        logger.info(f"User {user_id} viewing shortener")
        try:
            shortener_settings = await db.get_shortener(user_id)
            new_markup = await channel_manager.get_main_menu(user_id)
            if shortener_settings:
                test_link = await shortener.get_shortlink(db, "https://example.com", user_id)
                test_status = f"Test Link: <code>{test_link}</code>\n" if test_link and test_link.startswith("http") else "Test Link: Failed to generate, check API settings.\n"
                new_text = f"Current Shortener: 👀\nWebsite: <code>{shortener_settings['url']}</code>\nAPI: <code>{shortener_settings['api']}</code>\n{test_status}"
            else:
                new_text = "No shortener set! 🚫"
            if callback.message.text != new_text or callback.message.reply_markup != new_markup:
                await callback.message.edit_text(new_text, reply_markup=new_markup, parse_mode="HTML")
            await callback.answer()
            logger.info(f"Displayed shortener for user {user_id}")
        except Exception as e:
            logger.error(f"Error showing shortener for user {user_id}: {e}")
            await callback.message.reply("Failed to fetch shortener. Try again. 😕", reply_markup=await channel_manager.get_main_menu(user_id))

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
            await callback.message.reply("Failed to initiate backup link setup. Try again. 😕", reply_markup=await channel_manager.get_main_menu(user_id))

    @dp.callback_query(lambda c: c.data == "cancel_backup_link")
    async def cancel_backup_link(callback: types.CallbackQuery, state: FSMContext):
        user_id = callback.from_user.id
        logger.info(f"User {user_id} canceled backup link setup")
        try:
            await state.clear()
            await callback.message.edit_text("Backup link setup canceled. Returning to main menu... 😕", reply_markup=await channel_manager.get_main_menu(user_id))
            logger.info(f"Canceled backup link setup for user {user_id}")
            await callback.answer()
        except Exception as e:
            logger.error(f"Error canceling backup link setup for user {user_id}: {e}")
            await callback.message.reply("Failed to cancel. Try again. 😕", reply_markup=await channel_manager.get_main_menu(user_id))

    @dp.message(StateFilter(BotStates.SET_BACKUP_LINK))
    async def process_backup_link(message: types.Message, state: FSMContext):
        user_id = message.from_user.id
        logger.info(f"User {user_id} processing backup link")
        try:
            backup_link = message.text.strip()
            if not backup_link.startswith("http"):
                await message.reply("Invalid URL! Send a valid link starting with http:// or https://. 😕", reply_markup=await channel_manager.get_main_menu(user_id))
                logger.warning(f"Invalid backup link format by user {user_id}")
                return
            await db.save_group_settings(user_id, "backup_link", backup_link)
            await message.reply(f"Backup link set! ✅\nLink: <code>{backup_link}</code>", reply_markup=await channel_manager.get_main_menu(user_id), parse_mode="HTML")
            await state.clear()
            logger.info(f"Backup link set for user {user_id}")
        except Exception as e:
            logger.error(f"Error processing backup link for user {user_id}: {e}")
            await message.reply("Failed to set backup link. Try again. 😕", reply_markup=await channel_manager.get_main_menu(user_id))
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
            await callback.message.reply("Failed to initiate how to download setup. Try again. 😕", reply_markup=await channel_manager.get_main_menu(user_id))

    @dp.callback_query(lambda c: c.data == "cancel_how_to_download")
    async def cancel_how_to_download(callback: types.CallbackQuery, state: FSMContext):
        user_id = callback.from_user.id
        logger.info(f"User {user_id} canceled how to download setup")
        try:
            await state.clear()
            await callback.message.edit_text("How to Download setup canceled. Returning to main menu... 😕", reply_markup=await channel_manager.get_main_menu(user_id))
            logger.info(f"Canceled how to download setup for user {user_id}")
            await callback.answer()
        except Exception as e:
            logger.error(f"Error canceling how to download setup for user {user_id}: {e}")
            await callback.message.reply("Failed to cancel. Try again. 😕", reply_markup=await channel_manager.get_main_menu(user_id))

    @dp.message(StateFilter(BotStates.SET_HOW_TO_DOWNLOAD))
    async def process_how_to_download(message: types.Message, state: FSMContext):
        user_id = message.from_user.id
        logger.info(f"User {user_id} processing how to download")
        try:
            how_to_download = message.text.strip()
            if not how_to_download.startswith("http"):
                await message.reply("Invalid URL! Send a valid link starting with http:// or https://. 😕", reply_markup=await channel_manager.get_main_menu(user_id))
                logger.warning(f"Invalid how to download link format by user {user_id}")
                return
            await db.save_group_settings(user_id, "how_to_download", how_to_download)
            await message.reply(f"How to Download link set! ✅\nLink: <code>{how_to_download}</code>", reply_markup=await channel_manager.get_main_menu(user_id), parse_mode="HTML")
            await state.clear()
            logger.info(f"How to download link set for user {user_id}")
        except Exception as e:
            logger.error(f"Error processing how to download for user {user_id}: {e}")
            await message.reply("Failed to set how to download link. Try again. 😕", reply_markup=await channel_manager.get_main_menu(user_id))
            await state.clear()

    @dp.callback_query(lambda c: c.data == "get_search_bot")
    async def get_search_bot(callback: types.CallbackQuery, state: FSMContext):
        user_id = callback.from_user.id
        logger.info(f"User {user_id} adding clone bot")
        try:
            existing_clone = await db.get_clone_bot(user_id)
            if existing_clone:
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🗑️ Delete Search Bot", callback_data="delete_clone")],
                    [InlineKeyboardButton(text="⬅️ Back", callback_data="main_menu")]
                ])
                username = existing_clone.get('username', 'Unknown')
                new_text = f"You already have a search bot! 🤖\nUsername: <code>{username}</code>\nStart it with /start."
                if callback.message.text != new_text or callback.message.reply_markup != keyboard:
                    await callback.message.edit_text(new_text, reply_markup=keyboard, parse_mode="HTML")
                await callback.answer()
                logger.info(f"User {user_id} already has a clone bot")
                return
            await state.set_state(BotStates.SET_CLONE_TOKEN)
            await callback.message.edit_text(
                "Send the bot token for your search bot. 🤖\nObtain a token via @BotFather.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="Cancel ❌", callback_data="cancel_clone")]
                ])
            )
            await callback.answer()
            logger.info(f"Prompted user {user_id} to add clone bot token")
        except Exception as e:
            logger.error(f"Error prompting clone bot setup for user {user_id}: {e}")
            await callback.message.reply("Failed to initiate search bot setup. Try again. 😕", reply_markup=await channel_manager.get_main_menu(user_id))

    @dp.callback_query(lambda c: c.data == "cancel_clone")
    async def cancel_clone(callback: types.CallbackQuery, state: FSMContext):
        user_id = callback.from_user.id
        logger.info(f"User {user_id} canceled clone bot setup")
        try:
            await state.clear()
            await callback.message.edit_text("Search bot setup canceled. Returning to main menu... 😕", reply_markup=await channel_manager.get_main_menu(user_id))
            logger.info(f"Canceled clone bot setup for user {user_id}")
            await callback.answer()
        except Exception as e:
            logger.error(f"Error canceling clone bot setup for user {user_id}: {e}")
            await callback.message.reply("Failed to cancel. Try again. 😕", reply_markup=await channel_manager.get_main_menu(user_id))

    @dp.message(StateFilter(BotStates.SET_CLONE_TOKEN))
    async def process_clone_token(message: types.Message, state: FSMContext):
        user_id = message.from_user.id
        logger.info(f"User {user_id} processing clone bot token")
        try:
            token = message.text.strip()
            if not token.count(":") == 1 or len(token) < 35:
                raise ValueError("Invalid token format")
            test_bot = Bot(token=token)
            bot_info = await test_bot.get_me()
            username = f"@{bot_info.username}" if bot_info.username else "Unknown"
            await db.save_clone_bot(user_id, token, username)
            await message.reply(
                f"Search bot {username} added successfully! ✅\nStart your search bot with /start.",
                reply_markup=await channel_manager.get_main_menu(user_id),
                parse_mode="HTML"
            )
            await state.clear()
            logger.info(f"Clone bot {username} saved and validated for user {user_id}")
        except Exception as e:
            logger.error(f"Error adding clone bot for user {user_id}: {e}")
            await message.reply(f"Failed to add search bot: {str(e)} 😕\nSend a valid token.", reply_markup=await channel_manager.get_main_menu(user_id))
            await state.clear()

    @dp.callback_query(lambda c: c.data == "delete_clone")
    async def delete_clone(callback: types.CallbackQuery):
        user_id = callback.from_user.id
        logger.info(f"User {user_id} deleting clone bot")
        try:
            clone_bot = await db.get_clone_bot(user_id)
            if not clone_bot:
                await callback.message.edit_text("No search bot found! 🚫", reply_markup=await channel_manager.get_main_menu(user_id))
                logger.warning(f"No clone bot found for user {user_id}")
                await callback.answer()
                return
            username = clone_bot.get('username', 'Unknown')
            await db.delete_clone_bot(user_id)
            await callback.message.edit_text(f"Search bot {username} deleted successfully! ✅", reply_markup=await channel_manager.get_main_menu(user_id))
            logger.info(f"Deleted clone bot {username} for user {user_id}")
            await callback.answer()
        except Exception as e:
            logger.error(f"Error deleting clone bot for user {user_id}: {e}")
            await callback.message.reply("Failed to delete search bot. Try again. 😕", reply_markup=await channel_manager.get_main_menu(user_id))

    @dp.callback_query(lambda c: c.data == "clone_search")
    async def clone_search(callback: types.CallbackQuery, state: FSMContext):
        user_id = callback.from_user.id
        logger.info(f"User {user_id} initiating clone search")
        try:
            clone_bot = await db.get_clone_bot(user_id)
            if not clone_bot:
                new_text = "You need a search bot to use this feature! 🤖\nClick 'Get Your Search Bot' to set one up."
                if callback.message.text != new_text:
                    await callback.message.edit_text(new_text, reply_markup=await channel_manager.get_main_menu(user_id))
                logger.warning(f"No clone bot found for user {user_id} for clone search")
                await callback.answer()
                return
            await state.set_state(BotStates.SEARCH)
            await callback.message.edit_text(
                "Send the file name to search for. 🔍",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="Cancel ❌", callback_data="cancel_search")]
                ])
            )
            await callback.answer()
            logger.info(f"Prompted user {user_id} for clone search query")
        except Exception as e:
            logger.error(f"Error in clone search for user {user_id}: {e}")
            await callback.message.reply("Failed to initiate clone search. Try again. 😕", reply_markup=await channel_manager.get_main_menu(user_id))

    @dp.callback_query(lambda c: c.data == "cancel_search")
    async def cancel_search(callback: types.CallbackQuery, state: FSMContext):
        user_id = callback.from_user.id
        logger.info(f"User {user_id} canceled search")
        await state.clear()
        await callback.message.edit_text("Search canceled. 😕", reply_markup=await channel_manager.get_main_menu(user_id))
        await callback.answer()

    @dp.message(StateFilter(BotStates.SEARCH))
    async def process_search_query(message: types.Message, state: FSMContext):
        user_id = message.from_user.id
        query = message.text.strip()
        logger.info(f"User {user_id} searching for '{query}'")
        try:
            await search_manager.search_files(bot, user_id, query, message.chat.id, is_clone=True)
            await state.clear()
        except Exception as e:
            logger.error(f"Error processing search query '{query}' for user {user_id}: {e}")
            await message.reply("Failed to search files. Try again. 😕", reply_markup=await channel_manager.get_main_menu(user_id))
            await state.clear()

    @dp.callback_query(lambda c: c.data.startswith("file_"))
    async def serve_file(callback: types.CallbackQuery):
        user_id = callback.from_user.id
        data = callback.data.split("_")
        file_id = data[1]
        target_user_id = int(data[2])
        logger.info(f"User {user_id} requesting file {file_id}")
        try:
            await search_manager.serve_file(bot, target_user_id, file_id, callback.message.chat.id)
            await callback.answer()
        except Exception as e:
            logger.error(f"Error serving file {file_id} to user {user_id}: {e}")
            await callback.message.reply("Failed to serve file. Try again. 😕")
            await callback.answer()

    @dp.callback_query(lambda c: c.data == "set_fsub")
    async def set_fsub(callback: types.CallbackQuery, state: FSMContext):
        user_id = callback.from_user.id
        logger.info(f"User {user_id} setting force subscribe")
        try:
            if user_id not in ADMIN_IDS:
                new_text = "Only admins can set Force Subscribe! 🚫"
                if callback.message.text != new_text:
                    await callback.message.edit_text(new_text, reply_markup=await channel_manager.get_main_menu(user_id))
                await callback.answer()
                logger.warning(f"Unauthorized FSub attempt by user {user_id}")
                return
            await state.set_state(BotStates.SET_FSUB)
            new_text = "Send the channel ID (e.g., -100123456789) for Force Subscribe. Make me an admin in the channel. 📢\nSend 'disable' to turn off FSub."
            if callback.message.text != new_text:
                await callback.message.edit_text(
                    new_text,
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="Cancel ❌", callback_data="cancel_fsub")]
                    ])
                )
            await callback.answer()
            logger.info(f"Prompted user {user_id} to set FSub channel")
        except Exception as e:
            logger.error(f"Error prompting FSub setup for user {user_id}: {e}")
            await callback.message.reply("Failed to initiate FSub setup. Try again. 😕", reply_markup=await channel_manager.get_main_menu(user_id))

    @dp.callback_query(lambda c: c.data == "cancel_fsub")
    async def cancel_fsub(callback: types.CallbackQuery, state: FSMContext):
        user_id = callback.from_user.id
        logger.info(f"User {user_id} canceled FSub setup")
        try:
            await state.clear()
            await callback.message.edit_text("FSub setup canceled. Returning to main menu... 😕", reply_markup=await channel_manager.get_main_menu(user_id))
            logger.info(f"Canceled FSub setup for user {user_id}")
            await callback.answer()
        except Exception as e:
            logger.error(f"Error canceling FSub setup for user {user_id}: {e}")
            await callback.message.reply("Failed to cancel. Try again. 😕", reply_markup=await channel_manager.get_main_menu(user_id))

    @dp.message(StateFilter(BotStates.SET_FSUB))
    async def process_fsub(message: types.Message, state: FSMContext):
        user_id = message.from_user.id
        logger.info(f"User {user_id} processing FSub")
        try:
            input_text = message.text.strip()
            if input_text.lower() == "disable":
                await db.save_group_settings(user_id, "fsub_channel_id", None)
                await message.reply("Force Subscribe disabled! ✅", reply_markup=await channel_manager.get_main_menu(user_id))
                await state.clear()
                logger.info(f"FSub disabled by user {user_id}")
                return
            channel_id = int(input_text)
            if not str(channel_id).startswith("-100"):
                await message.reply("Invalid channel ID format. Use format like -100123456789 or 'disable'. 😕", reply_markup=await channel_manager.get_main_menu(user_id))
                logger.warning(f"Invalid FSub channel ID format by user {user_id}: {input_text}")
                return
            channel = await bot.get_chat(channel_id)
            if not await channel_manager.check_admin_status(bot, channel_id, bot.id):
                await message.reply(f"I’m not an admin in channel {channel.title or 'Unnamed Channel'}. Make me an admin and try again. 🚫", reply_markup=await channel_manager.get_main_menu(user_id))
                logger.warning(f"Bot not admin in FSub channel {channel_id} for user {user_id}")
                return
            await db.save_group_settings(user_id, "fsub_channel_id", channel_id)
            await message.reply(f"Force Subscribe set to {channel.title or 'Unnamed Channel'}! ✅", reply_markup=await channel_manager.get_main_menu(user_id))
            await state.clear()
            logger.info(f"FSub channel {channel_id} set by user {user_id}")
        except ValueError:
            await message.reply("Invalid channel ID. Please send a numeric ID like -100123456789 or 'disable'. 😕", reply_markup=await channel_manager.get_main_menu(user_id))
            logger.warning(f"Non-numeric FSub channel ID by user {user_id}: {input_text}")
        except Exception as e:
            logger.error(f"Error processing FSub for user {user_id}: {e}")
            await message.reply("Failed to set FSub. Try again. 😕", reply_markup=await channel_manager.get_main_menu(user_id))
            await state.clear()
