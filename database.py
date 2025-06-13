import logging
from motor.motor_asyncio import AsyncIOMotorClient
from config import MONGO_URI, DB_NAME, logger

class Database:
    def __init__(self):
        try:
            self.client = AsyncIOMotorClient(MONGO_URI)
            self.db = self.client[DB_NAME]
            logger.info("MongoDB connection established")
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            raise

    async def save_channel(self, user_id: int, channel_type: str, channel_id: int):
        try:
            await self.db.channels.update_one(
                {"user_id": user_id},
                {"$addToSet": {f"{channel_type}_channel_ids": channel_id}},
                upsert=True
            )
            logger.info(f"Saved {channel_type} channel {channel_id} for user {user_id}")
        except Exception as e:
            logger.error(f"Error saving {channel_type} channel {channel_id} for user {user_id}: {e}")
            raise

    async def get_channels(self, user_id: int, channel_type: str):
        try:
            doc = await self.db.channels.find_one({"user_id": user_id})
            channels = doc.get(f"{channel_type}_channel_ids", []) if doc else []
            logger.info(f"Fetched {len(channels)} {channel_type} channels for user {user_id}")
            return channels
        except Exception as e:
            logger.error(f"Error fetching {channel_type} channels for user {user_id}: {e}")
            return []

    async def save_shortener(self, user_id: int, url: str, api: str):
        try:
            await self.db.shorteners.update_one(
                {"user_id": user_id},
                {"$set": {"url": url, "api": api}},
                upsert=True
            )
            logger.info(f"Saved shortener for user {user_id}")
        except Exception as e:
            logger.error(f"Error saving shortener for user {user_id}: {e}")
            raise

    async def get_shortener(self, user_id: int):
        try:
            doc = await self.db.shorteners.find_one({"user_id": user_id})
            logger.info(f"Fetched shortener for user {user_id}")
            return doc
        except Exception as e:
            logger.error(f"Error fetching shortener for user {user_id}: {e}")
            return None

    async def save_media(self, user_id: int, media_type: str, file_id: str, file_name: str, raw_link: str, file_size: int):
        try:
            await self.db.media.insert_one({
                "user_id": user_id,
                "media_type": media_type,
                "file_id": file_id,
                "file_name": file_name,
                "raw_link": raw_link,
                "file_size": file_size
            })
            logger.info(f"Saved media {file_name} for user {user_id}")
        except Exception as e:
            logger.error(f"Error saving media for user {user_id}: {e}")
            raise

    async def get_user_media(self, user_id: int):
        try:
            media = await self.db.media.find({"user_id": user_id}).to_list(None)
            logger.info(f"Fetched {len(media)} media files for user {user_id}")
            return media
        except Exception as e:
            logger.error(f"Error fetching media for user {user_id}: {e}")
            return []

    async def save_group_settings(self, user_id: int, setting_key: str, setting_value: str):
        try:
            await self.db.settings.update_one(
                {"user_id": user_id},
                {"$set": {setting_key: setting_value}},
                upsert=True
            )
            logger.info(f"Saved setting {setting_key} for user {user_id}")
        except Exception as e:
            logger.error(f"Error saving setting {setting_key} for user {user_id}: {e}")
            raise

    async def get_settings(self, user_id: int):
        try:
            doc = await self.db.settings.find_one({"user_id": user_id})
            logger.info(f"Fetched settings for user {user_id}")
            return doc or {}
        except Exception as e:
            logger.error(f"Error fetching settings for user {user_id}: {e}")
            return {}

    async def save_clone_bot(self, user_id: int, token: str, username: str):
        try:
            await self.db.clones.update_one(
                {"user_id": user_id},
                {"$set": {"token": token, "username": username}},
                upsert=True
            )
            logger.info(f"Saved clone bot {username} for user {user_id}")
        except Exception as e:
            logger.error(f"Error saving clone bot for user {user_id}: {e}")
            raise

    async def get_clone_bot(self, user_id: int):
        try:
            doc = await self.db.clones.find_one({"user_id": user_id})
            logger.info(f"Fetched clone bot for user {user_id}")
            return doc
        except Exception as e:
            logger.error(f"Error fetching clone bot for user {user_id}: {e}")
            return None

    async def get_all_clone_bots(self):
        try:
            clones = await self.db.clones.find({}, {"user_id": 1, "token": 1, "username": 1, "_id": 0}).to_list(None)
            logger.info(f"Fetched {len(clones)} clone bots")
            return clones
        except Exception as e:
            logger.error(f"Error fetching all clone bots: {e}")
            return []
