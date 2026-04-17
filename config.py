import os
from dotenv import load_dotenv
from data.characters import characters5
load_dotenv()
CURRENT_RATE_UP_KEY = "flins"
CURRENT_RATE_UP_NAME = characters5.get(CURRENT_RATE_UP_KEY, "Flins")
BOT_TOKEN = os.getenv("BOT_TOKEN")
MONGO_URL = os.getenv("MONGO_URL")