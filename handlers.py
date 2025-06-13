from aiogram import Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import Command
import asyncio
from database import Database
from shortener import Shortener
import logging

logger = logging.getLogger(__name__)

class BotStates(StatesGroup):
    SET_POST_CHANNEL = State()
    SET_DATABASE_CHANNEL = State()
    SET_SHORTENER = State()
    SET_BACKUP_LINK = State()
    SET_HOW_TO_DOWNLOAD = State()

def get_main_menu():
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("Add Post Channel", callback_data="add_post_channel"))
    keyboard.add(InlineKeyboardButton("Add Database Channel", callback_data="add_database_channel"))
    keyboard.add(InlineKeyboardButton("Set Shortener", callback_data="set_shortener"))
    keyboard.add(InlineKeyboardButton("See Shortener", callback_data="see_shortener"))
    keyboard.add(InlineKeyboardButton("Set Backup Link", callback_data="set_backup_link"))
    keyboard.add(InlineKeyboardButton("Set How to Download", callback_data="set_how_to_download"))
    keyboard.add(InlineKeyboardButton("Total Files", callback_data="total_files"))
    keyboard.add(InlineKeyboardButton("Clone Search Bot", callback_data="clone_search_bot"))
    return keyboard

def register_handlers(dp: Dispatcher, db: Database, shortener: Shortener):
    ADMINS = [123456789]  # Replace with actual admin IDs

    @dp.message(Command("start"))
    async def start_command(message: types.Message):
        welcome_msg = (
            "Welcome to your personal storage bot! 📦\n"
            "I can save your media, auto-post to channels, and more.\n"
            "Let's get started!"
        )
        keyboard = InlineKeyboardMarkup()
        keyboard.add(InlineKeyboardButton("Let's Begin", callback_data="main_menu"))
        await message.reply(welcome_msg, reply_markup=keyboard)

    @dp.callback_query(lambda c: c.data == "main_menu")
    async def show_main_menu(callback: types.CallbackQuery):
        await callback.message.edit_text("Choose an option:", reply_markup=get_main_menu())

    @dp.callback_query(lambda c: c.data == "add_post_channel")
    async def add_post_channel(callback: types.CallbackQuery):
        await BotStates.SET_POST_CHANNEL.set()
        await callback.message.edit_text(
            "Please add me as an admin to your post channel and forward a message from that channel."
        )

    @dp.message(state=BotStates.SET_POST_CHANNEL)
    async def process_post_channel(message: types.Message, state: FSMContext):
        if message.forward_from_chat and message.forward_from_chat.type == "channel":
            channel_id = message.forward_from_chat.id
            channels = await db.get_channels(message.from_user.id, "post")
            if len(channels) >= 5:
                await message.reply("Max 5 post channels allowed!")
                await state.finish()
                return
            await db.save_channel(message.from_user.id, "post", channel_id)
            await message.reply("Post channel connected! Add more or go back.", reply_markup=get_main_menu())
            await state.finish()
        else:
            await message.reply("Please forward a message from a channel.")

    @dp.callback_query(lambda c: c.data == "add_database_channel")
    async def add_database_channel(callback: types.CallbackQuery):
        await BotStates.SET_DATABASE_CHANNEL.set()
        await callback.message.edit_text(
            "Please add me as an admin to your database channel and forward a message from that channel."
        )

    @dp.message(state=BotStates.SET_DATABASE_CHANNEL)
    async def process_database_channel(message: types.Message, state: FSMContext):
        if message.forward_from_chat and message.forward_from_chat.type == "channel":
            channel_id = message.forward_from_chat.id
            channels = await db.get_channels(message.from_user.id, "database")
            if len(channels) >= 5:
                await message.reply("Max 5 database channels allowed!")
                await state.finish()
                return
            await db.save_channel(message.from_user.id, "database", channel_id)
            await message.reply("Database channel connected! Add more or go back.", reply_markup=get_main_menu())
            await state.finish()
        else:
            await message.reply("Please forward a message from a channel.")

    @dp.message(Command("shortlink"))
    async def shortlink_command(message: types.Message):
        userid = message.from_user.id
        chat_type = message.chat.type
        grp_id = userid if chat_type == types.ChatType.PRIVATE else message.chat.id
        title = "PM" if chat_type == types.ChatType.PRIVATE else message.chat.title

        if chat_type != types.ChatType.PRIVATE:
            member = await message.bot.get_chat_member(grp_id, userid)
            if member.status not in ["administrator", "creator"] and str(userid) not in ADMINS:
                return await message.reply("<b>You don't have access to this command!</b>")

        try:
            _, shortlink_url, api = message.text.split(" ")
        except ValueError:
            return await message.reply(
                f"<b>Hey {message.from_user.mention}, command incomplete :(\n\nUse proper format!\n\nFormat:\n\n<code>/shortlink mdisk.link b6d97f6s96ds69d69d68d575d</code></b>"
            )

        reply = await message.reply("<b>Please wait...</b>")
        await db.save_shortener(grp_id, shortlink_url, api)
        await reply.edit_text(
            f"<b>Successfully added shortlink API for {title}\n\nCurrent shortlink website: <code>{shortlink_url}</code>\nCurrent API: <code>{api}</code>.</b>"
        )

    @dp.message(content_types=[types.ContentType.PHOTO, types.ContentType.VIDEO, types.ContentType.DOCUMENT])
    async def handle_media(message: types.Message):
        user_id = message.from_user.id
        database_channels = await db.get_channels(user_id, "database")
        if not database_channels or message.chat.id not in database_channels:
            return

        file_id = None
        file_name = None
        media_type = None
        if message.photo:
            file_id = message.photo[-1].file_id
            media_type = "photo"
            file_name = f"photo_{message.message_id}.jpg"
        elif message.video:
            file_id = message.video.file_id
            media_type = "video"
            file_name = message.video.file_name or f"video_{message.message_id}.mp4"
        elif message.document:
            file_id = message.document.file_id
            media_type = "document"
            file_name = message.document.file_name or f"doc_{message.message_id}"

        if file_id:
            raw_link = f"telegram://file/{file_id}"
            await db.save_media(user_id, media_type, file_id, file_name, raw_link)
            await asyncio.sleep(20)
            await post_media(user_id, file_name, raw_link, message.chat.id)

    async def post_media(user_id, file_name, raw_link, chat_id):
        shortener_settings = await db.get_shortener(chat_id)
        short_link = await shortener.get_shortlink(raw_link, chat_id)
        post_channels = await db.get_channels(user_id, "post")
        backup_link = (await db.get_settings(user_id)).get("backup_link", "")
        how_to_download = (await db.get_settings(user_id)).get("how_to_download", "")

        poster_url = await fetch_poster(file_name)

        keyboard = InlineKeyboardMarkup()
        keyboard.add(InlineKeyboardButton("Download", url=short_link))
        if backup_link:
            keyboard.add(InlineKeyboardButton("Backup Link", url=backup_link))
        if how_to_download:
            keyboard.add(InlineKeyboardButton("How to Download", url=how_to_download))

        for channel_id in post_channels:
            if poster_url:
                await message.bot.send_photo(channel_id, poster_url, caption=f"{file_name}\n{short_link}", reply_markup=keyboard)
            else:
                await message.bot.send_message(channel_id, f"{file_name}\n{short_link}", reply_markup=keyboard)

    async def fetch_poster(file_name):
        return None  # Implement Cinemagoer logic

    @dp.callback_query(lambda c: c.data == "total_files")
    async def show_total_files(callback: types.CallbackQuery):
        user_id = callback.from_user.id
        media_files = await db.get_user_media(user_id)
        await callback.message.edit_text(f"Total files: {len(media_files)}", reply_markup=get_main_menu())

    @dp.callback_query(lambda c: c.data == "clone_search_bot")
    async def clone_search_bot(callback: types.CallbackQuery):
        await callback.message.edit_text(
            "Clone search bot activated! Search for files in PM or connected groups.",
            reply_markup=get_main_menu()
        )

    @dp.message(Command("broadcast"))
    async def broadcast_command(message: types.Message):
        if message.from_user.id not in ADMINS:
            return
        await message.reply("Send the broadcast message.")

    @dp.message(Command("stats"))
    async def stats_command(message: types.Message):
        if message.from_user.id not in ADMINS:
            return
        total_users = await db.db.users.count_documents({})
        total_db_owners = await db.db.channels.count_documents({"channel_type": "database"})
        await message.reply(f"Users: {total_users}\nDatabase Owners: {total_db_owners}")

    @dp.callback_query(lambda c: c.data == "set_shortener")
    async def set_shortener(callback: types.CallbackQuery):
        await BotStates.SET_SHORTENER.set()
        await callback.message.edit_text(
            "Send the shortener details in format: <code>shortlink mdisk.link your_api_key</code>"
        )

    @dp.message(state=BotStates.SET_SHORTENER)
    async def process_shortener(message: types.Message, state: FSMContext):
        try:
            _, shortlink_url, api = message.text.split(" ")
        except ValueError:
            await message.reply(
                "Invalid format! Use: <code>shortlink mdisk.link your_api_key</code>"
            )
            return
        await db.save_shortener(message.from_user.id, shortlink_url, api)
        await message.reply(
            f"Shortener set!\nWebsite: <code>{shortlink_url}</code>\nAPI: <code>{api}</code>",
            reply_markup=get_main_menu()
        )
        await state.finish()

    @dp.callback_query(lambda c: c.data == "see_shortener")
    async def see_shortener(callback: types.CallbackQuery):
        shortener = await db.get_shortener(callback.from_user.id)
        if shortener:
            await callback.message.edit_text(
                f"Current Shortener:\nWebsite: <code>{shortener['url']}</code>\nAPI: <code>{shortener['api']}</code>",
                reply_markup=get_main_menu()
            )
        else:
            await callback.message.edit_text(
                "No shortener set!", reply_markup=get_main_menu()
            )
