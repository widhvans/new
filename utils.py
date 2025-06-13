import re
import logging
from imdb import Cinemagoer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='bot.log'
)
logger = logging.getLogger(__name__)

async def fetch_poster(file_name):
    logger.info(f"Fetching poster for file: {file_name}")
    try:
        ia = Cinemagoer()
        cleaned_name = clean_file_name(file_name)
        movies = ia.search_movie(cleaned_name)
        if movies:
            movie = ia.get_movie(movies[0].movieID)
            if 'cover url' in movie:
                poster_url = movie['cover url']
                logger.info(f"Poster URL fetched: {poster_url}")
                return poster_url
        logger.info(f"No poster found for {file_name}")
        return None
    except Exception as e:
        logger.error(f"Error fetching poster for {file_name}: {e}")
        return None

def clean_file_name(file_name):
    logger.info(f"Cleaning file name: {file_name}")
    # Remove episode/season tags and special characters
    cleaned = re.sub(r'[sS]\d+[eE]\d+|part\d+|[^\w\s]', '', file_name.lower()).strip()
    logger.info(f"Cleaned file name: {cleaned}")
    return cleaned
