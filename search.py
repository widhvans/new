"""Search and clone bot functionality."""
from pyrogram import Client, filters
from pymongo import MongoClient
from config import MONGO_URI, DB_NAME
from shortener import get_shortlink

client = MongoClient(MONGO_URI)
db = client[DB_NAME]
files_collection = db.files

def setup_search_handlers(app: Client):
    """Register search-related handlers."""
    
    @app.on_message(filters.command("search"))
    async def search_command(client, message):
        """Search files by name and return results with shortlinks."""
        query = message.text.split(" ", 1)[1] if len(message.text.split()) > 1 else ""
        if not query:
            return await message.reply("Please provide a search query.")

        results = files_collection.find({"file_name": {"$regex": query, "$options": "i"}}).limit(10)
        response = []
        for file in results:
            shortlink = await get_shortlink(file["universal_link"], message.chat.id)
            response.append(
                f"{file['file_name']} ({file['file_size']} bytes)\n"
                f"[Download]({shortlink})"
            )
        
        if response:
            await message.reply("\n".join(response), disable_web_page_preview=True)
        else:
            await message.reply("No results found.")
