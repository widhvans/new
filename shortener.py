"""URL shortener integration."""
import aiohttp
import logging
from pyrogram import Client, filters, enums
from config import SHORTLINK_URL, SHORTLINK_API, ENABLE_SHORTLINK, ADMINS
from pymongo import MongoClient
from config import MONGO_URI, DB_NAME

logger = logging.getLogger(__name__)
client = MongoClient(MONGO_URI)
db = client[DB_NAME]
settings_collection = db.settings

async def get_shortlink(link, chat_id=None, api_var=None, link_var=None):
    """Generate shortened link using provided logic."""
    if chat_id:
        settings = settings_collection.find_one({"chat_id": chat_id}) or {}
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

    if URL == "api.shareus.in":
        url = f"https://{URL}/shortLink"
        params = {"token": API, "format": "json", "link": link}
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, raise_for_status=True, ssl=False) as response:
                    data = await response.json(content_type="text/html")
                    if data["status"] == "success" and 'shortlink' in data:
                        return data["shortlink"]
                    else:
                        logger.error(f"Error: {data['message']}\nUrl Provider: {URL}")
                        return f'https://{URL}/shortlink?api={API}&link={link}'
        except Exception as e:
            logger.error(f"Error: {e}\nUrl Provider: {URL}")
            return f'https://{URL}/shortlink?token={API}&format=json&link={link}'
    elif 'rocklink' in URL:
        url = f'https://{URL}/api'
        params = {'api': API, 'url': link}
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, raise_for_status=True, ssl=False) as response:
                    data = await response.json()
                    if data["status"] == "success" and 'shortenedUrl' in data:
                        return data['shortenedUrl']
                    else:
                        logger.error(f"Error: {data['message']}\nUrl Provider: {URL}")
                        return f'https://{URL}/shortlink?api={API}&url={link}'
        except Exception as e:
            logger.error(f"Error: {e}\nUrl Provider: {URL}")
            return f'{URL}/shortlink?api={API}&url={link}'
    else:
        url = f'https://{URL}/api'
        params = {'api': API, 'url': link}
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, raise_for_status=True, ssl=False) as response:
                    data = await response.json()
                    if data["status"] == "success" and 'shortenedUrl' in data:
                        return data['shortenedUrl']
                    else:
                        logger.error(f"Error: {data['message']}\nUrl Provider: {URL}")
                        return f'https://{URL}/shortlink?api={API}&link={link}'
        except Exception as e:
            logger.error(f"Error: {e}\nUrl Provider: {URL}")
            return f'https://{URL}/shortlink?api={API}&link={link}'

async def get_verify_shorted_link(link):
    """Verify and shorten link."""
    API = SHORTLINK_API
    URL = SHORTLINK_URL
    https = link.split(":")[0]
    if "http" == https:
        https = "https"
        link = link.replace("http", https)
    if URL == "api.shareus.in":
        url = f"https://{URL}/shortLink"
        params = {"token": API, "format": "json", "link": link}
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, raise_for_status=True, ssl=False) as response:
                    data = await response.json(content_type="text/html")
                    if data["status"] == "success":
                        return data["shortlink"]
                    else:
                        logger.error(f"Error: {data['message']}")
                        return f'https://{URL}/shortLink?token={API}&format=json&link={link}'
        except Exception as e:
            logger.error(e)
            return f'https://{URL}/shortLink?token={API}&format=json&link={link}'
    else:
        url = f'https://{URL}/api'
        params = {'api': API, 'url': link}
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, raise_for_status=True, ssl=False) as response:
                    data = await response.json()
                    if data["status"] == "success":
                        return data['shortenedUrl']
                    else:
                        logger.error(f"Error: {data['message']}")
                        return f'https://{URL}/api?api={API}&link={link}'
        except Exception as e:
            logger.error(e)
            return f'{URL}/api?api={API}&link={link}'

def setup_shortener_handlers(app: Client):
    """Register shortener-related handlers."""
    
    @app.on_message(filters.command('shortlink'))
    async def shortlink_command(client, message):
        """Handle /shortlink command to set shortener."""
        userid = message.from_user.id if message.from_user else None
        if not userid:
            return await message.reply("You're an anonymous admin. Use /connect in PM.")

        chat_type = message.chat.type
        if chat_type == enums.ChatType.PRIVATE:
            grpid = settings_collection.find_one({"user_id": userid, "type": "active_connection"})
            if not grpid:
                return await message.reply("Not connected to any groups!")
            grp_id = grpid["chat_id"]
            try:
                chat = await client.get_chat(grp_id)
                title = chat.title
            except:
                return await message.reply("Check /connections to see your chats.")
        elif chat_type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
            grp_id = message.chat.id
            title = message.chat.title
        else:
            return await message.reply("Something went wrong.")

        user = await client.get_chat_member(grp_id, userid)
        if user.status not in [enums.ChatMemberStatus.ADMINISTRATOR, enums.ChatMemberStatus.OWNER] and userid not in ADMINS:
            return await message.reply("<b>You don't have access to this command!</b>")

        try:
            command, shorlink_url, api = message.text.split(" ")
        except ValueError:
            return await message.reply(
                f"<b>Hey {message.from_user.mention}, command incomplete :(\n\n"
                f"Use proper format!\n\nFormat:\n\n<code>/shortlink mdisk.link b6d97f6s96ds69d69d68d575d</code></b>"
            )

        reply = await message.reply("<b>Please wait...</b>")
        settings_collection.update_one(
            {"chat_id": grp_id},
            {"$set": {"shortlink": shorlink_url, "shortlink_api": api}},
            upsert=True
        )
        await reply.edit(
            f"<b>Successfully added shortlink API for {title}\n\n"
            f"Current shortlink website: <code>{shorlink_url}</code>\n"
            f"Current API: <code>{api}</code>.</b>"
        )
