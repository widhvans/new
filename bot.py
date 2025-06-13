import asyncio
import logging
from aiogram import Bot, Dispatcher
from config import TOKEN
from database import Database
from shortener import Shortener
from handlers import register_handlers

async def main():
    # Initialize logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    logger.info("Bot started")

    # Initialize bot and dispatcher
    bot = Bot(token=TOKEN)
    dp = Dispatcher()

    # Initialize database and shortener
    db = Database()
    await db.connect()
    shortener = Shortener()

    # Register handlers
    register_handlers(dp, db, shortener, bot)

    # Start polling
    try:
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Error in polling: {e}")
    finally:
        await db.disconnect()
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())
