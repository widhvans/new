import aiohttp
import logging
import re

logger = logging.getLogger(__name__)

async def fetch_poster(file_name):
    try:
        # Placeholder for Cinemagoer/IMDb poster fetching
        url = "https://api.example.com/poster"  # Replace with actual API
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params={"query": file_name}) as response:
                data = await response.json()
                return data.get("poster_url", None)
    except Exception as e:
        logger.error(f"Error fetching poster: {e}")
        return None

def clean_file_name(file_name):
    return re.sub(r'[^\w\s]', '', file_name.lower()).strip()
