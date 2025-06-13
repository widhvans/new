import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.utils.executor import start_polling
from config import TOKEN
from database import Database
from handlers import register_handlers
from shortener import Shortener

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot=bot, storage=storage)
db = Database()
shortener = Shortener()

async def on_startup():
    logger.info("Bot started")
    await db.connect()

async def on_shutdown():
    logger.info("Bot stopped")
    await db.disconnect()

if __name__ == "__main__":
    register_handlers(dp, db, shortener)
    start_polling(dp, skip_updates=True, on_startup=on_startup, on_shutdown=on_shutdown)
