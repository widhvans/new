import asyncio
import logging
import os
import sys
import psutil
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from config import BOT_TOKEN, MONGO_URI, logger
from database import Database
from shortener import Shortener
from handlers import register_handlers
from clone_bot import register_clone_handlers

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

async def start_bot(token: str, db: Database, is_clone: bool = False):
    try:
        bot = Bot(token=token)
        bot_info = await bot.get_me()
        logger.info(f"Starting {'clone' if is_clone else 'main'} bot with username @{bot_info.username}")
        storage = MemoryStorage()
        dp = Dispatcher(storage=storage)
        shortener = Shortener(db)
        if is_clone:
            register_clone_handlers(dp, db, shortener, bot)
        else:
            register_handlers(dp, db, shortener, bot)
        await bot.delete_webhook(drop_pending_updates=True)
        allowed_updates = ["message", "callback_query", "channel_post", "edited_message", "edited_channel_post"]
        for attempt in range(3):
            try:
                await dp.start_polling(bot, allowed_updates=allowed_updates, handle_as_tasks=True)
                logger.info(f"Bot @{bot_info.username} started successfully")
                break
            except Exception as e:
                logger.warning(f"Failed to start bot @{bot_info.username}, attempt {attempt + 1}/3: {e}")
                await asyncio.sleep(5 * (2 ** attempt))
        else:
            logger.error(f"Failed to start bot @{bot_info.username} after 3 attempts")
    except Exception as e:
        logger.error(f"Failed to initialize bot with token ending in {token[-4:]}: {e}")

async def main():
    check_single_instance()
    logger.info("Starting main bot...")
    db = Database()
    main_task = start_bot(BOT_TOKEN, db, is_clone=False)
    clone_bots = await db.get_all_clone_bots()
    logger.info(f"Found {len(clone_bots)} clone bots to start")
    clone_tasks = [start_bot(clone['token'], db, is_clone=True) for clone in clone_bots if 'token' in clone]
    tasks = [main_task] + clone_tasks
    await asyncio.gather(*tasks, return_exceptions=True)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Failed to start bot: {e}", exc_info=True)
