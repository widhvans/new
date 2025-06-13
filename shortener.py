import aiohttp
import logging
from config import SHORTLINK_URL, SHORTLINK_API, ENABLE_SHORTLINK, logger

def is_integer(value):
    try:
        int(value)
        return True
    except (ValueError, TypeError):
        return False

class Shortener:
    def __init__(self, db):
        self.db = db

    async def get_shortlink(self, db, link, chat_id=None, api_var=None, link_var=None):
        if chat_id and is_integer(chat_id):
            settings = await db.get_settings(chat_id)
            URL = settings.get('shortlink', SHORTLINK_URL) if api_var is None or link_var is None else link_var
            API = settings.get('shortlink_api', SHORTLINK_API) if api_var is None or link_var is None else api_var
            IS_SHORTLINK = settings.get('enable_shortlink', ENABLE_SHORTLINK)
        elif api_var and link_var:
            URL = link_var
            API = api_var
            IS_SHORTLINK = ENABLE_SHORTLINK
        else:
            URL = SHORTLINK_URL
            API = SHORTLINK_API
            IS_SHORTLINK = ENABLE_SHORTLINK

        URL = str(URL).strip()
        API = str(API).strip()

        if not IS_SHORTLINK:
            return link

        try:
            async with aiohttp.ClientSession() as session:
                if URL == "api.shareus.in":
                    url = f"https://{URL}/shortLink"
                    params = {"token": API, "format": "json", "link": link}
                    async with session.get(url, params=params, ssl=False) as response:
                        data = await response.json(content_type=None)
                        return data.get("shortlink", link) if data.get("status") == "success" else link
                else:
                    url = f"https://{URL}/api"
                    params = {"api": API, "url": link}
                    async with session.get(url, params=params, ssl=False) as response:
                        data = await response.json(content_type=None)
                        return data.get("shortenedUrl", link) if data.get("status") == "success" else link
        except Exception as e:
            logger.error(f"Error generating shortlink for link {link}: {e}")
            return link
