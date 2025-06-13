from pyrogram import Client, filters, enums
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from channel import get_user_settings, save_user_settings
from bot import app, logger

@app.on_callback_query(filters.regex("set_fsub"))
async def set_fsub(client, callback):
    user_id = callback.from_user.id
    logger.info(f"Set fsub initiated by user {user_id}")
    try:
        await callback.message.edit(
            "Send channel ID for forced subscription (e.g., -100123456789).",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Go Back", callback_data="main_menu")]])
        )
        await save_user_settings(user_id, "input_state", "set_fsub")
        logger.info(f"Waiting for fsub channel ID from user {user_id}")
    except Exception as e:
        logger.error(f"Error in set_fsub: {e}")
        await callback.message.edit("Error occurred. Try again.")

@app.on_message(filters.text & filters.private)
async def handle_fsub_input(client, message):
    user_id = message.from_user.id
    logger.info(f"Received fsub input from user {user_id}: {message.text}")
    try:
        settings = await get_user_settings(user_id)
        if settings.get("input_state") != "set_fsub":
            logger.info(f"No fsub input expected for user {user_id}")
            return
        channel_id = message.text.strip()
        chat = await client.get_chat(channel_id)
        await save_user_settings(user_id, "fsub_channel", channel_id)
        await save_user_settings(user_id, "input_state", None)
        await message.reply(f"Forced subscription set to {chat.title}!")
        logger.info(f"Fsub set to {channel_id} for user {user_id}")
        await message.reply(
            "What next?",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Go Back", callback_data="main_menu")]])
        )
    except Exception as e:
        logger.error(f"Error handling fsub input for user {user_id}: {e}")
        await message.reply("Invalid channel ID!")
        await message.reply(
            "What next?",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Go Back", callback_data="main_menu")]])
        )

@app.on_message(filters.private & ~filters.command(["start"]))
async def check_fsub(client, message):
    user_id = message.from_user.id
    logger.info(f"Checking fsub for user {user_id}")
    try:
        settings = await get_user_settings(user_id)
        fsub_channel = settings.get("fsub_channel")
        if not fsub_channel:
            logger.info(f"No fsub channel set for user {user_id}")
            return True
        member = await client.get_chat_member(fsub_channel, user_id)
        if member.status not in [enums.ChatMemberStatus.MEMBER, enums.ChatMemberStatus.ADMINISTRATOR, enums.ChatMemberStatus.OWNER]:
            chat = await client.get_chat(fsub_channel)
            buttons = [[InlineKeyboardButton("Join Channel", url=chat.invite_link)]]
            await message.reply(
                f"Please join {chat.title} to use the bot!",
                reply_markup=InlineKeyboardMarkup(buttons)
            )
            logger.info(f"User {user_id} not subscribed to fsub channel {fsub_channel}")
            return False
        logger.info(f"User {user_id} passed fsub check")
        return True
    except Exception as e:
        logger.error(f"Error checking fsub for user {user_id}: {e}")
        return True
