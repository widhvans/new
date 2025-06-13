import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.utils import executor
from config import TOKEN
from database import Database
from handlers import register_handlers
from shortener import Shortener

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)
db = Database()
shortener = Shortener()

async def on_startup(_):
    logger.info("Bot started")
    await db.connect()

async def on_shutdown(_):
    logger.info("Bot stopped")
    await db.disconnect()

if __name__ == "__main__":
    register_handlers(dp, db, shortener)
    executor.start_polling(dp, skip_updates=True, on_startup=on_startup, on_shutdown=on_shutdown)
