from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import logger, ADMIN_IDS

class AdminManager:
    def __init__(self, db):
        self.db = db

    async def broadcast(self, bot: Bot, user_id: int, message, target: str):
        if user_id not in ADMIN_IDS:
            await message.reply("You’re not authorized to use this command! 🚫")
            logger.warning(f"Unauthorized broadcast attempt by user {user_id}")
            return

        try:
            targets = []
            if target == "users":
                targets = await self.db.get_all_users()
            elif target == "database_owners":
                targets = await self.db.get_all_database_owners()
            elif target == "both":
                targets = list(set(await self.db.get_all_users() + await self.db.get_all_database_owners()))

            sent = 0
            for target_id in targets:
                try:
                    await bot.copy_message(target_id, message.chat.id, message.message_id)
                    sent += 1
                    await asyncio.sleep(0.1)  # Rate limit
                except Exception as e:
                    logger.warning(f"Failed to send broadcast to user {target_id}: {e}")
            await message.reply(f"Broadcast sent to {sent}/{len(targets)} {target}! 📢")
            logger.info(f"Broadcast sent to {sent}/{len(targets)} {target} by admin {user_id}")
        except Exception as e:
            logger.error(f"Error in broadcast by admin {user_id}: {e}")
            await message.reply("Failed to send broadcast. Try again. 😕")

    async def stats(self, bot: Bot, user_id: int, message):
        if user_id not in ADMIN_IDS:
            await message.reply("You’re not authorized to use this command! 🚫")
            logger.warning(f"Unauthorized stats attempt by user {user_id}")
            return

        try:
            total_users = len(await self.db.get_all_users())
            total_db_owners = len(await self.db.get_all_database_owners())
            await message.reply(f"📊 <b>Statistics</b>\n\nTotal Users: {total_users}\nDatabase Owners: {total_db_owners}", parse_mode="HTML")
            logger.info(f"Displayed stats to admin {user_id}")
        except Exception as e:
            logger.error(f"Error in stats for admin {user_id}: {e}")
            await message.reply("Failed to fetch stats. Try again. 😕")
