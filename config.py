import os

TOKEN = os.getenv("BOT_TOKEN", "your_bot_token_here")
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DB_NAME = "telegram_bot"
SHORTLINK_URL = "api.shareus.in"
SHORTLINK_API = "your_shortlink_api_key"
ENABLE_SHORTLINK = True
