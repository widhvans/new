from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from channel import get_user_settings, save_user_settings
from bot import app, logger

@app.on_callback_query(filters.regex("set_fsub"))
async def set_fsub(client, callback):
    user_id = callback.from_user.id
    await callback.message.edit(
        "Send channel ID for forced subscription (e.g., -100123456789).",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Go Back", callback_data="main_menu")]])
    )
    app.add_handler(
        filters.text & filters.user(user_id) & filters.private,
        lambda c, m: handle_fsub(c, m, user_id)
    )

async def handle_fsub(client, message, user_id):
    channel_id = message.text.strip()
    try:
        chat = await client.get_chat(channel_id)
        await save_user_settings(user_id, "fsub_channel", channel_id)
        await message.reply(f"Forced subscription set to {chat.title}!")
    except Exception as e:
        logger.error(f"Error setting fsub: {e}")
        await message.reply("Invalid channel ID!")
    await message.reply(
        "What next?",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Go Back", callback_data="main_menu")]])
    )

@app.on_message(filters.private & ~filters.command(["start"]))
async def check_fsub(client, message):
    user_id = message.from_user.id
    settings = await get_user_settings(user_id)
    fsub_channel = settings.get("fsub_channel")
    if not fsub_channel:
        return
    try:
        member = await client.get_chat_member(fsub_channel, user_id)
        if member.status not in [enums.ChatMemberStatus.MEMBER, enums.ChatMemberStatus.ADMINISTRATOR, enums.ChatMemberStatus.OWNER]:
            chat = await client.get_chat(fsub_channel)
            buttons = [[InlineKeyboardButton("Join Channel", url=chat.invite_link)]]
            await message.reply(
                f"Please join {chat.title} to use the bot!",
                reply_markup=InlineKeyboardMarkup(buttons)
            )
            return False
    except Exception:
        pass
    return True
