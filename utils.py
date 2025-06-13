import aiohttp
import logging
import re

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def fetch_poster(file_name):
    logger.info(f"Fetching poster for file: {file_name}")
    try:
        # Placeholder for Cinemagoer/IMDb poster fetching
        url = "https://api.example.com/poster"  # Replace with actual API
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params={"query": file_name}) as response:
                data = await response.json()
                poster_url = data.get("poster_url", None)
                logger.info(f"Poster URL fetched: {poster_url}")
                return poster_url
    except Exception as e:
        logger.error(f"Error fetching poster: {e}")
        return None

def clean_file_name(file_name):
    logger.info(f"Cleaning file name: {file_name}")
    cleaned = re.sub(r'[^\w\s]', '', file_name.lower()).strip()
    logger.info(f"Cleaned file name: {cleaned}")
    return cleaned
