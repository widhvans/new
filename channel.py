from pyrogram import Client, filters, enums
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database import settings_collection
from bot import app, logger

async def get_user_settings(user_id):
    logger.info(f"Fetching settings for user {user_id}")
    try:
        settings = await settings_collection.find_one({"user_id": user_id})
        logger.info(f"Settings fetched for user {user_id}: {settings}")
        return settings or {}
    except Exception as e:
        logger.error(f"Error fetching settings for user {user_id}: {e}")
        return {}

async def save_user_settings(user_id, key, value):
    logger.info(f"Saving setting {key} for user {user_id}")
    try:
        await settings_collection.update_one(
            {"user_id": user_id},
            {"$set": {key: value}},
            upsert=True
        )
        logger.info(f"Setting {key} saved for user {user_id}")
    except Exception as e:
        logger.error(f"Error saving setting {key} for user {user_id}: {e}")

@app.on_callback_query(filters.regex("add_post_channel"))
async def add_post_channel(client, callback):
    user_id = callback.from_user.id
    logger.info(f"Add post channel button clicked by user {user_id}")
    try:
        settings = await get_user_settings(user_id)
        post_channels = settings.get("post_channels", [])
        if len(post_channels) >= 5:
            await callback.message.edit("Max 5 post channels allowed!")
            await callback.answer("Limit reached!")
            logger.warning(f"User {user_id} attempted to add more than 5 post channels")
            return
        await callback.message.edit(
            "Send channel ID (e.g., -100123456789). Make me admin first!",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Go Back", callback_data="main_menu")]])
        )
        await save_user_settings(user_id, "input_state", "add_post_channel")
        await callback.answer("Please send channel ID.")
        logger.info(f"Waiting for post channel ID from user {user_id}")
    except Exception as e:
        logger.error(f"Error in add_post_channel: {e}")
        await callback.message.edit("Error occurred. Try again.")
        await callback.answer("Error occurred!")

@app.on_callback_query(filters.regex("add_db_channel"))
async def add_db_channel(client, callback):
    user_id = callback.from_user.id
    logger.info(f"Add database channel button clicked by user {user_id}")
    try:
        settings = await get_user_settings(user_id)
        db_channels = settings.get("db_channels", [])
        if len(db_channels) >= 5:
            await callback.message.edit("Max 5 database channels allowed!")
            await callback.answer("Limit reached!")
            logger.warning(f"User {user_id} attempted to add more than 5 db channels")
            return
        await callback.message.edit(
            "Send channel ID (e.g., -100123456789). Make me admin first!",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Go Back", callback_data="main_menu")]])
        )
        await save_user_settings(user_id, "input_state", "add_db_channel")
        await callback.answer("Please send channel ID.")
        logger.info(f"Waiting for database channel ID from user {user_id}")
    except Exception as e:
        logger.error(f"Error in add_db_channel: {e}")
        await callback.message.edit("Error occurred. Try again.")
        await callback.answer("Error occurred!")

@app.on_message(filters.text & filters.private)
async def handle_channel_input(client, message):
    user_id = message.from_user.id
    logger.info(f"Received text input from user {user_id}: {message.text}")
    try:
        settings = await get_user_settings(user_id)
        input_state = settings.get("input_state")
        if input_state not in ["add_post_channel", "add_db_channel"]:
            logger.info(f"No channel input expected for user {user_id}")
            return
        channel_type = "post_channels" if input_state == "add_post_channel" else "db_channels"
        channel_id = message.text.strip()
        logger.info(f"Processing channel ID {channel_id} for {channel_type} by user {user_id}")
        chat = await client.get_chat(channel_id)
        admins = await client.get_chat_members(channel_id, filter=enums.ChatMembersFilter.ADMINISTRATORS)
        bot_id = (await client.get_me()).id
        if not any(admin.user.id == bot_id for admin in admins):
            await message.reply("I'm not an admin in this channel!")
            logger.warning(f"Bot not admin in channel {channel_id} for user {user_id}")
            return
        channels = settings.get(channel_type, [])
        if channel_id not in channels:
            channels.append(channel_id)
            await save_user_settings(user_id, channel_type, channels)
            await message.reply(f"{channel_type.replace('_', ' ').title()} connected!")
            logger.info(f"Channel {channel_id} added to {channel_type} for user {user_id}")
        else:
            await message.reply("Channel already connected!")
            logger.info(f"Channel {channel_id} already connected for user {user_id}")
        await save_user_settings(user_id, "input_state", None)
        buttons = [
            [InlineKeyboardButton(f"Add More {channel_type.replace('_', ' ').title()}", callback_data=f"add_{channel_type}")],
            [InlineKeyboardButton("Go Back", callback_data="main_menu")]
        ]
        await message.reply("What next?", reply_markup=InlineKeyboardMarkup(buttons))
    except Exception as e:
        logger.error(f"Error handling channel input for user {user_id}: {e}")
        await message.reply("Invalid channel ID or error occurred!")
        await save_user_settings(user_id, "input_state", None)
