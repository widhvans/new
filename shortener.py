import aiohttp
import logging
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from bot import get_user_settings, save_user_settings
from config import SHORTLINK_URL, SHORTLINK_API, ENABLE_SHORTLINK, BOT_USERNAME

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='bot.log'
)
logger = logging.getLogger(__name__)

async def get_shortlink(link, user_id=None, api_var=None, link_var=None):
    logger.info(f"Generating short link for user {user_id}: {link}")
    try:
        if user_id:
            settings = await get_user_settings(user_id)
            URL = settings.get('shortlink', SHORTLINK_URL) if not link_var else link_var
            API = settings.get('shortlink_api', SHORTLINK_API) if not api_var else api_var
            IS_SHORTLINK = settings.get('enable_shortlink', ENABLE_SHORTLINK)
        else:
            URL = SHORTLINK_URL
            API = SHORTLINK_API
            IS_SHORTLINK = ENABLE_SHORTLINK

        URL = str(URL).strip()
        API = str(API).strip()

        if not IS_SHORTLINK:
            logger.info("Shortlink disabled, returning raw link")
            return link

        if URL == "api.shareus.in":
            url = f"https://{URL}/shortLink"
            params = {"token": API, "format": "json", "link": link}
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, ssl=False) as response:
                    response.raise_for_status()
                    data = await response.json(content_type=None)
                    if data["status"] == "success" and 'shortlink' in data:
                        logger.info(f"Short link generated: {data['shortlink']}")
                        return data["shortlink"]
                    else:
                        logger.error(f"Error: {data.get('message', 'Unknown error')}")
                        return link
        elif 'rocklink' in URL:
            url = f"https://{URL}/api"
            params = {'api': API, 'url': link}
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, ssl=False) as response:
                    response.raise_for_status()
                    data = await response.json()
                    if data["status"] == "success" and 'shortenedUrl' in data:
                        logger.info(f"Short link generated: {data['shortenedUrl']}")
                        return data['shortenedUrl']
                    else:
                        logger.error(f"Error: {data.get('message', 'Unknown error')}")
                        return link
        else:
            url = f"https://{URL}/api"
            params = {'api': API, 'url': link}
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, ssl=False) as response:
                    response.raise_for_status()
                    data = await response.json()
                    if data["status"] == "success" and 'shortenedUrl' in data:
                        logger.info(f"Short link generated: {data['shortenedUrl']}")
                        return data['shortenedUrl']
                    else:
                        logger.error(f"Error: {data.get('message', 'Unknown error')}")
                        return link
    except Exception as e:
        logger.error(f"Error generating short link for user {user_id}: {e}")
        return link

async def get_verify_shorted_link(link):
    logger.info(f"Verifying short link: {link}")
    try:
        API = SHORTLINK_API
        URL = SHORTLINK_URL
        https = link.split(":")[0]
        if "http" == https:
            link = link.replace("http", "https")
        if URL == "api.shareus.in":
            url = f"https://{URL}/shortLink"
            params = {"token": API, "format": "json", "link": link}
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, ssl=False) as response:
                    response.raise_for_status()
                    data = await response.json(content_type=None)
                    if data["status"] == "success":
                        logger.info(f"Verified short link: {data['shortlink']}")
                        return data["shortlink"]
                    else:
                        logger.error(f"Error: {data.get('message', 'Unknown error')}")
                        return link
        else:
            url = f"https://{URL}/api"
            params = {'api': API, 'url': link}
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, ssl=False) as response:
                    response.raise_for_status()
                    data = await response.json()
                    if data["status"] == "success":
                        logger.info(f"Verified short link: {data['shortenedUrl']}")
                        return data['shortenedUrl']
                    else:
                        logger.error(f"Error: {data.get('message', 'Unknown error')}")
                        return link
    except Exception as e:
        logger.error(f"Error verifying short link: {e}")
        return link

@app.on_message(filters.command('shortlink') & filters.private)
async def shortlink(client, message):
    logger.info(f"Shortlink command received from user {message.from_user.id}")
    try:
        user_id = message.from_user.id
        data = message.text.split(" ", 2)
        if len(data) != 3:
            await message.reply(
                f"Hey {message.from_user.mention}, use the correct format!\n\n"
                f"Example: <code>/shortlink earn4link.in your_api_key</code>",
                quote=True
            )
            return

        _, shorlink_url, api = data
        await save_user_settings(user_id, 'shortlink', shorlink_url)
        await save_user_settings(user_id, 'shortlink_api', api)
        await message.reply(
            f"Shortener set successfully!\n\n"
            f"Website: <code>{shorlink_url}</code>\nAPI: <code>{api}</code>",
            quote=True
        )
        logger.info(f"Shortener set for user {user_id}: {shorlink_url}, {api}")
    except Exception as e:
        logger.error(f"Error in shortlink command for user {user_id}: {e}")
        await message.reply("Error setting shortener. Try again.", quote=True)

@app.on_callback_query(filters.regex("set_shortener"))
async def set_shortener(client, callback):
    user_id = callback.from_user.id
    logger.info(f"Set shortener initiated by user {user_id}")
    try:
        new_text = "Send shortener URL and API (e.g., earn4link.in your_api_key)"
        if callback.message.text != new_text:
            await callback.message.edit(
                new_text,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Go Back", callback_data="main_menu")]])
            )
        await save_user_settings(user_id, "input_state", "set_shortener")
        await callback.answer("Please send shortener details.")
        logger.info(f"Waiting for shortener input from user {user_id}")
    except Exception as e:
        logger.error(f"Error in set_shortener for user {user_id}: {e}")
        await callback.message.edit("Error occurred. Try again.")
        await callback.answer("Error occurred!")

@app.on_callback_query(filters.regex("see_shortener"))
async def see_shortener(client, callback):
    user_id = callback.from_user.id
    logger.info(f"See shortener requested by user {user_id}")
    try:
        settings = await get_user_settings(user_id)
        url = settings.get("shortlink", SHORTLINK_URL)
        api = settings.get("shortlink_api", SHORTLINK_API)
        new_text = f"Current Shortener:\nURL: {url}\nAPI: {api}"
        if callback.message.text != new_text:
            await callback.message.edit(
                new_text,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Go Back", callback_data="main_menu")]])
            )
        await callback.answer()
        logger.info(f"Shortener details displayed for user {user_id}")
    except Exception as e:
        logger.error(f"Error in see_shortener for user {user_id}: {e}")
        await callback.message.edit("Error occurred. Try again.")
        await callback.answer("Error occurred!")
