from pyrogram import Client, filters, enums
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from bot import app, logger, get_user_settings, save_user_settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='bot.log'
)
logger = logging.getLogger(__name__)

@app.on_message(filters.private & ~filters.command(["start"]))
async def check_fsub(client, message):
    user_id = message.from_user.id
    logger.info(f"Checking fsub for user {user_id}")
    try:
        settings = await get_user_settings(user_id)
        fsub_channel = settings.get("fsub_channel")
        if not fsub_channel:
            logger.info(f"No fsub channel set for user {user_id}")
            return True
        member = await client.get_chat_member(fsub_channel, user_id)
        if member.status not in [enums.ChatMemberStatus.MEMBER, enums.ChatMemberStatus.ADMINISTRATOR, enums.ChatMemberStatus.OWNER]:
            chat = await client.get_chat(fsub_channel)
            buttons = [[InlineKeyboardButton("Join Channel", url=chat.invite_link)]]
            await message.reply(
                f"Please join {chat.title} to use the bot!",
                reply_markup=InlineKeyboardMarkup(buttons)
            )
            logger.info(f"User {user_id} not subscribed to fsub channel {fsub_channel}")
            return False
        logger.info(f"User {user_id} passed fsub check")
        return True
    except Exception as e:
        logger.error(f"Error checking fsub for user {user_id}: {e}")
        return True
