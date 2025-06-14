"""Broadcast functionality for admins."""
from pyrogram import Client, filters
from config import ADMINS
from pymongo import MongoClient
from config import MONGO_URI, DB_NAME

client = MongoClient(MONGO_URI)
db = client[DB_NAME]
users_collection = db.users

def setup_broadcast_handlers(app: Client):
    """Register broadcast handlers."""
    
    @app.on_message(filters.command("broadcast") & filters.user(ADMINS))
    async def broadcast_command(client, message):
        """Broadcast message to all users or DB owners."""
        try:
            target = message.text.split(" ", 1)[1]
            msg = message.reply_to_message or message
            users = users_collection.find() if "all" in target else users_collection.find({"is_db_owner": True})
            
            for user in users:
                try:
                    await msg.copy(user["user_id"])
                except Exception as e:
                    print(f"Failed to broadcast to {user['user_id']}: {e}")
            await message.reply("Broadcast sent!")
        except Exception as e:
            await message.reply(f"Error: {e}")
