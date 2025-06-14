"""Channel connection and management."""
from pyrogram import Client, filters, enums
from pymongo import MongoClient
from config import MONGO_URI, DB_NAME
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

client = MongoClient(MONGO_URI)
db = client[DB_NAME]
channels_collection = db.channels

def setup_channel_handlers(app: Client):
    """Register channel-related handlers."""
    
    @app.on_callback_query(filters.regex("manage_channels"))
    async def manage_channels(client, query):
        """Display connected channels and management options."""
        user_id = query.from_user.id
        channels = channels_collection.find({"user_id": user_id})
        text = "Connected Channels:\n"
        for ch in channels:
            text += f"- {ch['type']}: {ch['chat_id']} ({'active' if ch['active'] else 'inactive'})\n"
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Add Post Channel", callback_data="add_post_channel")],
            [InlineKeyboardButton("Add DB Channel", callback_data="add_db_channel")],
            [InlineKeyboardButton("Remove Channel", callback_data="remove_channel")],
            [InlineKeyboardButton("Go Back", callback_data="main_menu")]
        ])
        await query.message.edit(text or "No channels connected.", reply_markup=keyboard)
    
    @app.on_message(filters.command("addchannel"))
    async def add_channel_command(client, message):
        """Add a new channel for posting or storage."""
        try:
            chat_id = message.chat.id
            user_id = message.from_user.id
            chat = await client.get_chat(chat_id)
            if chat.type not in [enums.ChatType.CHANNEL]:
                return await message.reply("This command only works in channels.")
            
            member = await client.get_chat_member(chat_id, user_id)
            if member.status not in [enums.ChatMemberStatus.ADMINISTRATOR, enums.ChatMemberStatus.OWNER]:
                return await message.reply("You need to be an admin to connect this channel.")
            
            channels_collection.update_one(
                {"chat_id": chat_id, "user_id": user_id},
                {"$set": {"type": "post", "active": True}},
                upsert=True
            )
            await message.reply("Channel connected successfully!")
        except Exception as e:
            await message.reply(f"Error: {e}")
