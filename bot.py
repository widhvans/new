import asyncio
import logging
from pyrogram import Client, filters, enums
from config import API_ID, API_HASH, BOT_TOKEN
from interface import setup_handlers
from storage import handle_file_upload
from shortener import setup_shortener_handlers
from broadcast import setup_broadcast_handlers
from search import setup_search_handlers
from poster import setup_poster_handlers

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Client("StorageBot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

def main():
    """Initialize bot and register handlers."""
    setup_handlers(app)
    handle_file_upload(app)
    setup_shortener_handlers(app)
    setup_broadcast_handlers(app)
    setup_search_handlers(app)
    setup_poster_handlers(app)
    app.run()

if __name__ == "__main__":
    main()
