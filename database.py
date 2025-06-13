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
        try:
            self.client = AsyncIOMotorClient(MONGO_URI)
            self.db = self.client[DB_NAME]
            logger.info("Successfully connected to MongoDB")
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            raise

    async def disconnect(self):
        try:
            if self.client:
                self.client.close()
                logger.info("Successfully disconnected from MongoDB")
        except Exception as e:
            logger.error(f"Error disconnecting from MongoDB: {e}")

    async def save_media(self, user_id, media_type, file_id, file_name, raw_link, file_size=None):
        try:
            document = {
                "user_id": user_id,
                "media_type": media_type,
                "file_id": file_id,
                "file_name": file_name,
                "raw_link": raw_link,
                "file_size": str(file_size) if file_size else "Unknown",
                "created_at": datetime.now()
            }
            result = await self.db.media.insert_one(document)
            logger.info(f"Saved media {file_name} (type: {media_type}) for user {user_id}, ID: {result.inserted_id}")
            return result
        except Exception as e:
            logger.error(f"Error saving media for user {user_id}: {e}")
            raise

    async def get_user_media(self, user_id):
        try:
            media = await self.db.media.find({"user_id": user_id}).to_list(None)
            logger.info(f"Fetched {len(media)} media files for user {user_id}")
            return media
        except Exception as e:
            logger.error(f"Error fetching media for user {user_id}: {e}")
            return []

    async def save_channel(self, user_id, channel_type, channel_id):
        try:
            result = await self.db.channels.update_one(
                {"user_id": user_id, "channel_type": channel_type},
                {"$addToSet": {"channel_ids": channel_id}},
                upsert=True
            )
            logger.info(f"Saved channel {channel_id} ({channel_type}) for user {user_id}")
            return result
        except Exception as e:
            logger.error(f"Error saving channel for user {user_id}: {e}")
            raise

    async def get_channels(self, user_id, channel_type):
        try:
            result = await self.db.channels.find_one({"user_id": user_id, "channel_type": channel_type})
            channels = result.get("channel_ids", []) if result else []
            logger.info(f"Fetched {len(channels)} {channel_type} channels for user {user_id}")
            return channels
        except Exception as e:
            logger.error(f"Error fetching channels for user {user_id}: {e}")
            return []

    async def save_shortener(self, chat_id, shortener_url, shortener_api):
        try:
            result = await self.db.shorteners.update_one(
                {"chat_id": chat_id},
                {"$set": {"url": shortener_url, "api": shortener_api}},
                upsert=True
            )
            logger.info(f"Saved shortener for chat {chat_id}")
            return result
        except Exception as e:
            logger.error(f"Error saving shortener for chat {chat_id}: {e}")
            raise

    async def get_shortener(self, chat_id):
        try:
            shortener = await self.db.shorteners.find_one({"chat_id": chat_id})
            logger.info(f"Fetched shortener for chat {chat_id}: {bool(shortener)}")
            return shortener
        except Exception as e:
            logger.error(f"Error fetching shortener for chat {chat_id}: {e}")
            return None

    async def get_settings(self, chat_id):
        try:
            settings = await self.db.settings.find_one({"chat_id": chat_id}) or {}
            result = {
                "shortlink": settings.get("shortlink", ""),
                "shortlink_api": settings.get("shortlink_api", ""),
                "enable_shortlink": settings.get("enable_shortlink", True),
                "backup_link": settings.get("backup_link", ""),
                "how_to_download": settings.get("how_to_download", "")
            }
            logger.info(f"Fetched settings for chat {chat_id}")
            return result
        except Exception as e:
            logger.error(f"Error fetching settings for chat {chat_id}: {e}")
            return {}

    async def save_group_settings(self, chat_id, key, value):
        try:
            result = await self.db.settings.update_one(
                {"chat_id": chat_id},
                {"$set": {key: value}},
                upsert=True
            )
            logger.info(f"Saved setting {key} for chat {chat_id}")
            return result
        except Exception as e:
            logger.error(f"Error saving settings for chat {chat_id}: {e}")
            raise

    async def save_clone_bot(self, user_id, token):
        try:
            result = await self.db.clone_bots.update_one(
                {"user_id": user_id},
                {"$set": {"token": token, "created_at": datetime.now()}},
                upsert=True
            )
            logger.info(f"Saved clone bot token for user {user_id}")
            return result
        except Exception as e:
            logger.error(f"Error saving clone bot for user {user_id}: {e}")
            raise

    async def get_clone_bot(self, user_id):
        try:
            clone_bot = await self.db.clone_bots.find_one({"user_id": user_id})
            logger.info(f"Fetched clone bot for user {user_id}: {bool(clone_bot)}")
            return clone_bot
        except Exception as e:
            logger.error(f"Error fetching clone bot for user {user_id}: {e}")
            return None
