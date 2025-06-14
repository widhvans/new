
"""Configuration for bot and MongoDB."""
import os

# Telegram Bot Token
BOT_TOKEN = os.getenv("BOT_TOKEN", "7320891454:AAHp3AAIZK2RKIkWyYIByB_fSEq9Xuk9-bk")

# MongoDB connection URI
MONGO_URI = os.getenv("MONGO_URI", "mongodb+srv://soniji:chaloji@cluster0.i5zy74f.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")

# MongoDB database name
DB_NAME = "telegram_bot"

# Default shortlink service URL
SHORTLINK_URL = "earn4link.in"

# Shortlink service API key
SHORTLINK_API = "987ef01cfd538490d733c3341926742e779421e2"

# Enable/disable shortlink feature
ENABLE_SHORTLINK = True

# Bot username (with @ prefix)
BOT_USERNAME = "@Complete_jwshw_bot"

# List of admin user IDs
ADMINS = {1938030055}

# Telegram API ID
API_ID = os.getenv("API_ID", "10389378")

# Telegram API Hash
API_HASH = os.getenv("API_HASH", "cdd5c820cb6abeecaef38e2bb8db4860")
