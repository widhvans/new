from database import settings_collection
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='bot.log'
)
logger = logging.getLogger(__name__)

async def get_user_settings(user_id):
    logger.info(f"Fetching settings for user {user_id}")
    try:
        settings = await settings_collection.find_one({"user_id": user_id})
        logger.info(f"Settings fetched for user {user_id}: {settings}")
        return settings or {}
    except Exception as e:
        logger.error(f"Error fetching settings for user {user_id}: {e}")
        return {}

async def save_user_settings(user_id, key, value):
    logger.info(f"Saving setting {key} for user {user_id}")
    try:
        await settings_collection.update_one(
            {"user_id": user_id},
            {"$set": {key: value}},
            upsert=True
        )
        logger.info(f"Setting {key} saved for user {user_id}")
    except Exception as e:
        logger.error(f"Error saving setting {key} for user {user_id}: {e}")
