import aiohttp
import logging
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from channel import get_user_settings, save_user_settings
from config import SHORTLINK_URL, SHORTLINK_API, ENABLE_SHORTLINK
from bot import app, logger

async def get_shortlink(link, user_id=None, api_var=None, link_var=None):
    logger.info(f"Generating shortlink for user {user_id}: {link}")
    try:
        settings = await get_user_settings(user_id) if user_id else {}
        URL = settings.get('shortlink', SHORTLINK_URL) if not link_var else link_var
        API = settings.get('shortlink_api', SHORTLINK_API) if not api_var else api_var
        if not ENABLE_SHORTLINK:
            logger.info("Shortlink disabled, returning original link")
            return link
        url = f"https://{URL}/shortLink"
        params = {"token": API, "format": "json", "link": link}
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, ssl=False) as response:
                data = await response.json(content_type="text/html")
                short_link = data["shortlink"] if data["status"] == "success" else link
                logger.info(f"Shortlink generated: {short_link}")
                return short_link
    except Exception as e:
        logger.error(f"Error shortening link for user {user_id}: {e}")
        return link

@app.on_callback_query(filters.regex("set_shortener"))
async def set_shortener(client, callback):
    user_id = callback.from_user.id
    logger.info(f"Set shortener initiated by user {user_id}")
    try:
        await callback.message.edit(
            "Send shortener URL and API (e.g., earn4link.in your_api_key)",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Go Back", callback_data="main_menu")]])
        )
        await save_user_settings(user_id, "input_state", "set_shortener")
        logger.info(f"Waiting for shortener input from user {user_id}")
    except Exception as e:
        logger.error(f"Error in set_shortener: {e}")
        await callback.message.edit("Error occurred. Try again.")

@app.on_callback_query(filters.regex("see_shortener"))
async def see_shortener(client, callback):
    user_id = callback.from_user.id
    logger.info(f"See shortener requested by user {user_id}")
    try:
        settings = await get_user_settings(user_id)
        url = settings.get("shortlink", SHORTLINK_URL)
        api = settings.get("shortlink_api", SHORTLINK_API)
        await callback.message.edit(
            f"Current Shortener:\nURL: {url}\nAPI: {api}",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Go Back", callback_data="main_menu")]])
        )
        logger.info(f"Shortener details displayed for user {user_id}")
    except Exception as e:
        logger.error(f"Error in see_shortener: {e}")
        await callback.message.edit("Error occurred. Try again.")

@app.on_message(filters.text & filters.private)
async def handle_shortener_input(client, message):
    user_id = message.from_user.id
    logger.info(f"Received shortener input from user {user_id}: {message.text}")
    try:
        settings = await get_user_settings(user_id)
        if settings.get("input_state") != "set_shortener":
            logger.info(f"No shortener input expected for user {user_id}")
            return
        url, api = message.text.strip().split()
        await save_user_settings(user_id, "shortlink", url)
        await save_user_settings(user_id, "shortlink_api", api)
        await save_user_settings(user_id, "input_state", None)
        await message.reply("Shortener set successfully!")
        logger.info(f"Shortener set for user {user_id}: {url}, {api}")
        await message.reply(
            "What next?",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Go Back", callback_data="main_menu")]])
        )
    except ValueError:
        logger.warning(f"Invalid shortener format from user {user_id}")
        await message.reply("Invalid format! Use: shortener_url api_key")
    except Exception as e:
        logger.error(f"Error handling shortener input for user {user_id}: {e}")
        await message.reply("Error occurred. Try again.")
