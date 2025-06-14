"""Configuration for bot and MongoDB."""
from os import environ

API_ID = environ.get("API_ID", "your_api_id")
API_HASH = environ.get("API_HASH", "your_api_hash")
BOT_TOKEN = environ.get("BOT_TOKEN", "your_bot_token")
MONGO_URI = environ.get("MONGO_URI", "mongodb://localhost:27017")
DB_NAME = "StorageBotDB"
ADMINS = set(map(int, environ.get("ADMINS", "123456789").split(",")))
SHORTLINK_URL = environ.get("SHORTLINK_URL", "api.shareus.in")
SHORTLINK_API = environ.get("SHORTLINK_API", "your_shortlink_api")
ENABLE_SHORTLINK = bool(environ.get("ENABLE_SHORTLINK", True))
