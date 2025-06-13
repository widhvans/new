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

    async def save_media(self, user_id, media_type, file_id, file_name, raw_link):
        await self.db.media.insert_one({
            "user_id": user_id,
            "media_type": media_type,
            "file_id": file_id,
            "file_name": file_name,
            "raw_link": raw_link,
            "created_at": datetime.now()
        })

    async def get_user_media(self, user_id):
        return await self.db.media.find({"user_id": user_id}).to_list(None)

    async def save_channel(self, user_id, channel_type, channel_id):
        await self.db.channels.update_one(
            {"user_id": user_id, "channel_type": channel_type},
            {"$addToSet": {"channel_ids": channel_id}},
            upsert=True
        )

    async def get_channels(self, user_id, channel_type):
        result = await self.db.channels.find_one({"user_id": user_id, "channel_type": channel_type})
        return result.get("channel_ids", []) if result else []

    async def save_shortener(self, chat_id, shortener_url, shortener_api):
        await self.db.shorteners.update_one(
            {"chat_id": chat_id},
            {"$set": {"url": shortener_url, "api": shortener_api}},
            upsert=True
        )

    async def get_shortener(self, chat_id):
        return await self.db.shorteners.find_one({"chat_id": chat_id})

    async def get_settings(self, chat_id):
        settings = await self.db.settings.find_one({"chat_id": chat_id}) or {}
        return {
            "shortlink": settings.get("shortlink", ""),
            "shortlink_api": settings.get("shortlink_api", ""),
            "enable_shortlink": settings.get("enable_shortlink", True),
            "backup_link": settings.get("backup_link", ""),
            "how_to_download": settings.get("how_to_download", "")
        }

    async def save_group_settings(self, chat_id, key, value):
        await self.db.settings.update_one(
            {"chat_id": chat_id},
            {"$set": {key: value}},
            upsert=True
        )
