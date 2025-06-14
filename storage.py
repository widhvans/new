"""File storage and database channel management."""
from pyrogram import Client, filters
from pymongo import MongoClient
from config import MONGO_URI, DB_NAME
from datetime import datetime

client = MongoClient(MONGO_URI)
db = client[DB_NAME]
files_collection = db.files
channels_collection = db.channels

async def handle_file_upload(app: Client):
    """Handle file uploads and store in MongoDB."""
    
    @app.on_message(filters.document | filters.video | filters.audio | filters.photo)
    async def store_file(client, message):
        """Store uploaded file in MongoDB and return universal link."""
        user_id = message.from_user.id
        file = message.document or message.video or message.audio or message.photo
        file_id = file.file_id
        file_name = getattr(file, "file_name", "unnamed_file")
        file_size = getattr(file, "file_size", 0)
        
        # Store file metadata
        file_data = {
            "user_id": user_id,
            "file_id": file_id,
            "file_name": file_name,
            "file_size": file_size,
            "upload_date": datetime.utcnow(),
            "universal_link": f"storagebot:{file_id}"
        }
        files_collection.insert_one(file_data)
        
        # Send universal link to user
        await message.reply(f"File stored! Universal link: `{file_data['universal_link']}`")
