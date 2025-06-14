"""IMDB/Cinemagoer poster fetching."""
from pyrogram import Client
from cinemagoer import IMDb
from pymongo import MongoClient
from config import MONGO_URI, DB_NAME

client = MongoClient(MONGO_URI)
db = client[DB_NAME]
settings_collection = db.settings

def setup_poster_handlers(app: Client):
    """Register poster-related handlers."""
    
    async def fetch_poster(title):
        """Fetch movie/series poster from IMDB."""
        imdb = IMDb()
        results = imdb.search_movie(title)
        if not results:
            return None
        movie = imdb.get_movie(results[0].movieID)
        return movie.get("cover url")
    
    @app.on_message(filters.command("toggle_poster"))
    async def toggle_poster(client, message):
        """Toggle poster inclusion in posts."""
        chat_id = message.chat.id
        current = settings_collection.find_one({"chat_id": chat_id}) or {}
        new_state = not current.get("use_poster", True)
        settings_collection.update_one(
            {"chat_id": chat_id},
            {"$set": {"use_poster": new_state}},
            upsert=True
        )
        await message.reply(f"Poster inclusion {'enabled' if new_state else 'disabled'}.")
