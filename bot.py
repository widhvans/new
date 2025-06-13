import asyncio
import logging
import os
import sys
import psutil
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from config import BOT_TOKEN, BOT_USERNAME, MONGO_URI, logger
from database import Database
from shortener import Shortener
from handlers import register_handlers

def check_single_instance():
    pid_file = "bot.pid"
    if os.path.exists(pid_file):
        with open(pid_file, "r") as f:
            pid = int(f.read().strip())
        if psutil.pid_exists(pid):
            logger.error(f"Bot already running with PID {pid}. Exiting.")
            sys.exit(1)
    with open(pid_file, "w") as f:
        f.write(str(os.getpid()))

async def start_bot(token: str, db: Database):
    try:
        bot = Bot(token=token)
        storage = MemoryStorage()
        dp = Dispatcher(storage=storage)
        shortener = Shortener()
        register_handlers(dp, db, shortener, bot)
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot, allowed_updates=["message", "callback_query"])
        logger.info(f"Bot started with token ending in {token[-4:]}")
    except Exception as e:
        logger.error(f"Failed to start bot with token ending in {token[-4:]}: {e}")

async def main():
    check_single_instance()
    logger.info("Starting main bot...")
    db = Database()  # Initialize single Database instance
    await start_bot(BOT_TOKEN, db)
    # Start clone bots
    clone_bots = await db.get_all_clone_bots()
    tasks = [start_bot(clone['token'], db) for clone in clone_bots]
    if tasks:
        logger.info(f"Starting {len(tasks)} clone bots...")
        await asyncio.gather(*tasks)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Failed to start bot: {e}", exc_info=True)
