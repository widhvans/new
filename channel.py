from pyrogram import Client, filters, enums
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database import settings_collection
from bot import app, logger

async def get_user_settings(user_id):
    settings = await settings_collection.find_one({"user_id": user_id})
    return settings or {}

async def save_user_settings(user_id, key, value):
    await settings_collection.update_one(
        {"user_id": user_id},
        {"$set": {key: value}},
        upsert=True
    )

@app.on_callback_query(filters.regex("add_post_channel"))
async def add_post_channel(client, callback):
    user_id = callback.from_user.id
    settings = await get_user_settings(user_id)
    post_channels = settings.get("post_channels", [])
    if len(post_channels) >= 5:
        await callback.message.edit("Max 5 post channels allowed!")
        return
    await callback.message.edit(
        "Send channel ID (e.g., -100123456789). Make me admin first!",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Go Back", callback_data="main_menu")]])
    )
    app.add_handler(
        filters.text & filters.user(user_id) & filters.private,
        lambda c, m: handle_channel_id(c, m, user_id, "post_channels")
    )

@app.on_callback_query(filters.regex("add_db_channel"))
async def add_db_channel(client, callback):
    user_id = callback.from_user.id
    settings = await get_user_settings(user_id)
    db_channels = settings.get("db_channels", [])
    if len(db_channels) >= 5:
        await callback.message.edit("Max 5 database channels allowed!")
        return
    await callback.message.edit(
        "Send channel ID (e.g., -100123456789). Make me admin first!",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Go Back", callback_data="main_menu")]])
    )
    app.add_handler(
        filters.text & filters.user(user_id) & filters.private,
        lambda c, m: handle_channel_id(c, m, user_id, "db_channels")
    )

async def handle_channel_id(client, message, user_id, channel_type):
    channel_id = message.text.strip()
    try:
        chat = await client.get_chat(channel_id)
        admins = await client.get_chat_members(channel_id, filter=enums.ChatMembersFilter.ADMINISTRATORS)
        bot_id = (await client.get_me()).id
        if not any(admin.user.id == bot_id for admin in admins):
            await message.reply("I'm not an admin in this channel!")
            return
        settings = await get_user_settings(user_id)
        channels = settings.get(channel_type, [])
        if channel_id not in channels:
            channels.append(channel_id)
            await save_user_settings(user_id, channel_type, channels)
            await message.reply(f"{channel_type.replace('_', ' ').title()} connected!")
        else:
            await message.reply("Channel already connected!")
    except Exception as e:
        logger.error(f"Error connecting channel: {e}")
        await message.reply("Invalid channel ID or error occurred!")
    buttons = [
        [InlineKeyboardButton(f"Add More {channel_type.replace('_', ' ').title()}", callback_data=f"add_{channel_type}")],
        [InlineKeyboardButton("Go Back", callback_data="main_menu")]
    ]
    await message.reply("What next?", reply_markup=InlineKeyboardMarkup(buttons))
