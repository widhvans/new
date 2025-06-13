import os
import logging

TOKEN = os.getenv("BOT_TOKEN", "7320891454:AAHp3AAIZK2RKIkWyYIByB_fSEq9Xuk9-bk")
MONGO_URI = os.getenv("MONGO_URI", "mongodb+srv://soniji:chaloji@cluster0.i5zy74f.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
DB_NAME = "telegram_bot"
SHORTLINK_URL = "earn4link.in"
SHORTLINK_API = "987ef01cfd538490d733c3341926742e779421e2"
ENABLE_SHORTLINK = True
BOT_USERNAME = "@Complete_jwshw_bot"

# Logging Configuration
logging.basicConfig(
    level=logging.WARNING,  # Suppress INFO logs, show WARNING and above
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("bot.log"),
        logging.StreamHandler()
    ]
)
logging.getLogger("aiogram").setLevel(logging.WARNING)  # Suppress aiogram INFO logs
logging.getLogger("database").setLevel(logging.WARNING)  # Suppress database INFO logs
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)  # Enable DEBUG for custom logs
