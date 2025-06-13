import os
import logging
from logging.handlers import RotatingFileHandler

TOKEN = os.getenv("BOT_TOKEN", "7320891454:AAHp3AAIZK2RKIkWyYIByB_fSEq9Xuk9-bk")
MONGO_URI = os.getenv("MONGO_URI", "mongodb+srv://soniji:chaloji@cluster0.i5zy74f.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
DB_NAME = "telegram_bot"
SHORTLINK_URL = "earn4link.in"
SHORTLINK_API = "987ef01cfd538490d733c3341926742e779421e2"
ENABLE_SHORTLINK = True
BOT_USERNAME = "@Complete_jwshw_bot"

# Logging Configuration
logger = logging.getLogger()
logger.setLevel(logging.INFO)  # Set root logger to INFO
for handler in logger.handlers[:]:  # Clear existing handlers
    logger.removeHandler(handler)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
file_handler = RotatingFileHandler("bot.log", maxBytes=10*1024*1024, backupCount=5)  # 10MB, 5 backups
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(formatter)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(formatter)
logger.addHandler(file_handler)
logger.addHandler(console_handler)
logging.getLogger("aiogram").setLevel(logging.WARNING)  # Suppress aiogram INFO logs
logging.getLogger("motor").setLevel(logging.WARNING)  # Suppress motor INFO logs
