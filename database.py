from motor.motor_asyncio import AsyncIOMotorClient
from config import MONGO_URI, DB_NAME
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class Database:
    def __init__(self):
        self.client = None
        self.db = None

    async def connect(self):
        self.client = AsyncIOMotorClient(MONGO_URI)
        self.db = self.client[DB_NAME]
        logger.info("Connected to MongoDB")

    async def disconnect(self):
        if self.client:
            self.client.close()
            logger.info("Disconnected from MongoDB")

    async def save_media(self, user_id, media_type, file_id, file_name, raw_link, file_size=None):
        try:
            await self.db.media.insert_one({
                "user_id": user_id,
                "media_type": media_type,
                "file_id": file_id,
                "file_name": file_name,
                "raw_link": raw_link,
                "file_size": file_size,
                "created_at": datetime.now()
            })
        except Exception as e:
            logger.error(f"Error saving media for user {user_id}: {e}")

    async def get_user_media(self, user_id):
        try:
            return await self.db.media.find({"user_id": user_id}).to_list(None)
        except Exception as e:
            logger.error(f"Error fetching media for user {user_id}: {e}")
            return []

    async def save_channel(self, user_id, channel_type, channel_id):
        try:
            await self.db.channels.update_one(
                {"user_id": user_id, "channel_type": channel_type},
                {"$addToSet": {"channel_ids": channel_id}},
                upsert=True
            )
        except Exception as e:
            logger.error(f"Error saving channel for user {user_id}: {e}")

    async def get_channels(self, user_id, channel_type):
        try:
            result = await self.db.channels.find_one({"user_id": user_id, "channel_type": channel_type})
            return result.get("channel_ids", []) if result else []
        except Exception as e:
            logger.error(f"Error fetching channels for user {user_id}: {e}")
            return []

    async def save_shortener(self, chat_id, shortener_url, shortener_api):
        try:
            await self.db.shorteners.update_one(
                {"chat_id": chat_id},
                {"$set": {"url": shortener_url, "api": shortener_api}},
                upsert=True
            )
        except Exception as e:
            logger.error(f"Error saving shortener for chat {chat_id}: {e}")

    async def get_shortener(self, chat_id):
        try:
            return await self.db.shorteners.find_one({"chat_id": chat_id})
        except Exception as e:
            logger.error(f"Error fetching shortener for chat {chat_id}: {e}")
            return None

    async def get_settings(self, chat_id):
        try:
            settings = await self.db.settings.find_one({"chat_id": chat_id}) or {}
            return {
                "shortlink": settings.get("shortlink", ""),
                "shortlink_api": settings.get("shortlink_api", ""),
                "enable_shortlink": settings.get("enable_shortlink", True),
                "backup_link": settings.get("backup_link", ""),
                "how_to_download": settings.get("how_to_download", "")
            }
        except Exception as e:
            logger.error(f"Error fetching settings for chat {chat_id}: {e}")
            return {}

    async def save_group_settings(self, chat_id, key, value):
        try:
            await self.db.settings.update_one(
                {"chat_id": chat_id},
                {"$set": {key: value}},
                upsert=True
            )
        except Exception as e:
            logger.error(f"Error saving settings for chat {chat_id}: {e}")

    async def save_clone_bot(self, user_id, token):
        try:
            await self.db.clone_bots.update_one(
                {"user_id": user_id},
                {"$set": {"token": token, "created_at": datetime.now()}},
                upsert=True
            )
        except Exception as e:
            logger.error(f"Error saving clone bot for user {user_id}: {e}")
            raise

    async def get_clone_bot(self, user_id):
        try:
            return await self.db.clone_bots.find_one({"user_id": user_id})
        except Exception as e:
            logger.error(f"Error fetching clone bot for user {user_id}: {e}")
            return None
