import motor.motor_asyncio
import os
from datetime import datetime
from config import MONGO_URI, logger

class Database:
    def __init__(self):
        try:
            self.client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URI)
            self.db = self.client["telegram_bot"]
            logger.info("MongoDB connection established")
            asyncio.create_task(self.test_connection())
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            raise

    async def test_connection(self):
        try:
            test_collection = self.db["test"]
            await test_collection.insert_one({"test": "connection_check", "timestamp": datetime.utcnow()})
            logger.info("MongoDB test insert successful")
            await test_collection.delete_one({"test": "connection_check"})
        except Exception as e:
            logger.error(f"MongoDB test insert failed: {e}")

    async def save_user(self, user_id: int):
        logger.debug(f"Saving user {user_id}")
        try:
            await self.db.users.update_one(
                {"user_id": user_id},
                {"$set": {"user_id": user_id, "timestamp": datetime.utcnow()}},
                upsert=True
            )
            logger.info(f"User {user_id} saved")
        except Exception as e:
            logger.error(f"Error saving user {user_id}: {e}")

    async def get_settings(self, user_id: int):
        logger.debug(f"Fetching settings for user {user_id}")
        try:
            settings = await self.db.settings.find_one({"user_id": user_id}) or {}
            logger.info(f"Fetched settings for user {user_id}: {settings}")
            return settings
        except Exception as e:
            logger.error(f"Error fetching settings for user {user_id}: {e}")
            return {}

    async def save_group_settings(self, user_id: int, key: str, value):
        logger.debug(f"Saving setting {key}={value} for user {user_id}")
        try:
            await self.db.settings.update_one(
                {"user_id": user_id},
                {"$set": {key: value, "timestamp": datetime.utcnow()}},
                upsert=True
            )
            logger.info(f"Saved setting {key} for user {user_id}")
        except Exception as e:
            logger.error(f"Error saving setting {key} for user {user_id}: {e}")

    async def save_media(self, user_id: int, media_type: str, file_id: str, file_name: str, raw_link: str, file_size: int, metadata: dict):
        logger.debug(f"Saving media {file_name} for user {user_id}")
        try:
            media_doc = {
                "user_id": user_id,
                "media_type": media_type,
                "file_id": file_id,
                "file_name": file_name,
                "raw_link": raw_link,
                "file_size": file_size,
                "metadata": metadata,
                "timestamp": datetime.utcnow()
            }
            result = await self.db.media.insert_one(media_doc)
            logger.info(f"Saved media {file_name} for user {user_id} with ID {result.inserted_id}")
        except Exception as e:
            logger.error(f"Error saving media {file_name} for user {user_id}: {e}")
            raise

    async def get_user_media(self, user_id: int):
        logger.debug(f"Fetching media for user {user_id}")
        try:
            media_files = await self.db.media.find({"user_id": user_id}).to_list(None)
            logger.info(f"Fetched {len(media_files)} media files for user {user_id}")
            return media_files
        except Exception as e:
            logger.error(f"Error fetching media for user {user_id}: {e}")
            return []

    async def save_channel(self, user_id: int, channel_type: str, channel_id: int):
        logger.debug(f"Saving {channel_type} channel {channel_id} for user {user_id}")
        try:
            key = "post_channel_ids" if channel_type == "post" else "database_channel_ids"
            await self.db.channels.update_one(
                {"user_id": user_id},
                {"$addToSet": {key: channel_id}, "$set": {"timestamp": datetime.utcnow()}},
                upsert=True
            )
            logger.info(f"Saved {channel_type} channel {channel_id} for user {user_id}")
        except Exception as e:
            logger.error(f"Error saving {channel_type} channel {channel_id} for user {user_id}: {e}")

    async def get_channels(self, user_id: int, channel_type: str):
        logger.debug(f"Fetching {channel_type} channels for user {user_id}")
        try:
            key = "post_channel_ids" if channel_type == "post" else "database_channel_ids"
            channels = await self.db.channels.find_one({"user_id": user_id}) or {}
            channel_ids = channels.get(key, [])
            logger.info(f"Fetched {len(channel_ids)} {channel_type} channels for user {user_id}: {channel_ids}")
            return channel_ids
        except Exception as e:
            logger.error(f"Error fetching {channel_type} channels for user {user_id}: {e}")
            return []

    async def save_shortener(self, user_id: int, url: str, api: str):
        logger.debug(f"Saving shortener for user {user_id}")
        try:
            await self.db.shorteners.update_one(
                {"user_id": user_id},
                {"$set": {"url": url, "api": api, "timestamp": datetime.utcnow()}},
                upsert=True
            )
            logger.info(f"Saved shortener for user {user_id}")
        except Exception as e:
            logger.error(f"Error saving shortener for user {user_id}: {e}")

    async def get_shortener(self, user_id: int):
        logger.debug(f"Fetching shortener for user {user_id}")
        try:
            shortener = await self.db.shorteners.find_one({"user_id": user_id})
            logger.info(f"Fetched shortener for user {user_id}: {shortener}")
            return shortener
        except Exception as e:
            logger.error(f"Error fetching shortener for user {user_id}: {e}")
            return None

    async def save_clone_bot(self, user_id: int, token: str, username: str):
        logger.debug(f"Saving clone bot for user {user_id}")
        try:
            await self.db.clone_bots.update_one(
                {"user_id": user_id},
                {"$set": {"token": token, "username": username, "timestamp": datetime.utcnow()}},
                upsert=True
            )
            logger.info(f"Saved clone bot {username} for user {user_id}")
        except Exception as e:
            logger.error(f"Error saving clone bot for user {user_id}: {e}")

    async def get_clone_bot(self, user_id: int):
        logger.debug(f"Fetching clone bot for user {user_id}")
        try:
            clone_bot = await self.db.clone_bots.find_one({"user_id": user_id})
            logger.info(f"Fetched clone bot for user {user_id}: {clone_bot}")
            return clone_bot
        except Exception as e:
            logger.error(f"Error fetching clone bot for user {user_id}: {e}")
            return None

    async def delete_clone_bot(self, user_id: int):
        logger.debug(f"Deleting clone bot for user {user_id}")
        try:
            await self.db.clone_bots.delete_one({"user_id": user_id})
            logger.info(f"Deleted clone bot for user {user_id}")
        except Exception as e:
            logger.error(f"Error deleting clone bot for user {user_id}: {e}")

    async def get_all_clone_bots(self):
        logger.debug("Fetching all clone bots")
        try:
            clone_bots = await self.db.clone_bots.find().to_list(None)
            logger.info(f"Fetched {len(clone_bots)} clone bots")
            return clone_bots
        except Exception as e:
            logger.error(f"Error fetching all clone bots: {e}")
            return []
