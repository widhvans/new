from database import users_collection
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def save_user(user_id):
    logger.info(f"Saving user {user_id}")
    try:
        await users_collection.update_one(
            {"user_id": user_id},
            {"$set": {"user_id": user_id}},
            upsert=True
        )
        logger.info(f"User {user_id} saved successfully")
    except Exception as e:
        logger.error(f"Error saving user {user_id}: {e}")
