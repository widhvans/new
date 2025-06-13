from motor.motor_asyncio import AsyncIOMotorClient
from config import MONGO_URI

mongo_client = AsyncIOMotorClient(MONGO_URI)
db = mongo_client["telegram_bot"]
users_collection = db["users"]
media_collection = db["media"]
settings_collection = db["settings"]
