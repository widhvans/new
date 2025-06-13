import aiohttp
import logging
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from channel import get_user_settings, save_user_settings
from config import DEFAULT_SHORTLINK_URL, DEFAULT_SHORTLINK_API
from bot import app, logger

async def get_shortlink(link, user_id=None, api_var=None, link_var=None):
    settings = await get_user_settings(user_id) if user_id else {}
    URL = settings.get('shortlink', DEFAULT_SHORTLINK_URL) if not link_var else link_var
    API = settings.get('shortlink_api', DEFAULT_SHORTLINK_API) if not api_var else api_var
    url = f"https://{URL}/shortLink"
    params = {"token": API, "format": "json", "link": link}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, ssl=False) as response:
                data = await response.json(content_type="text/html")
                return data["shortlink"] if data["status"] == "success" else link
    except Exception as e:
        logger.error(f"Error shortening link: {e}")
        return link

@app.on_callback_query(filters.regex("set_shortener"))
async def set_shortener(client, callback):
    user_id = callback.from_user.id
    await callback.message.edit(
        "Send shortener URL and API (e.g., api.shareus.in your_api_key)",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Go Back", callback_data="main_menu")]])
    )
    app.add_handler(
        filters.text & filters.user(user_id) & filters.private,
        lambda c, m: handle_shortener(c, m, user_id)
    )

async def handle_shortener(client, message, user_id):
    try:
        url, api = message.text.strip().split()
        await save_user_settings(user_id, "shortlink", url)
        await save_user_settings(user_id, "shortlink_api", api)
        await message.reply("Shortener set successfully!")
    except ValueError:
        await message.reply("Invalid format! Use: shortener_url api_key")
    await message.reply(
        "What next?",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Go Back", callback_data="main_menu")]])
    )

@app.on_callback_query(filters.regex("see_shortener"))
async def see_shortener(client, callback):
    user_id = callback.from_user.id
    settings = await get_user_settings(user_id)
    url = settings.get("shortlink", DEFAULT_SHORTLINK_URL)
    api = settings.get("shortlink_api", DEFAULT_SHORTLINK_API)
    await callback.message.edit(
        f"Current Shortener:\nURL: {url}\nAPI: {api}",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Go Back", callback_data="main_menu")]])
    )
