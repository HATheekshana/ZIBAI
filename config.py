import os
from dotenv import load_dotenv
from data.characters import characters5
load_dotenv()
CURRENT_RATE_UP_KEY = "lauma"
CURRENT_RATE_UP_NAME = characters5.get(CURRENT_RATE_UP_KEY, "Lauma")
BOT_TOKEN = os.getenv("BOT_TOKEN")
MONGO_URL = os.getenv("MONGO_URL")
TWITTER_BEARER_TOKEN = os.getenv("TWITTER_BEARER_TOKEN")
TWITTER_USERNAMES = [
    username.strip()
    for username in os.getenv("TWITTER_USERNAMES", "").split(",")
    if username.strip()
]
RSS_URL = os.getenv("RSS_URL", "https://www.hoyolab.com/feed")
ADMIN_VAL = os.getenv("ADMIN_ID")
ADMIN_ID = int(ADMIN_VAL)
KEY = os.getenv("ENCRYPTION_KEY").encode()
cookies = {
    "ltuid_v2": os.getenv("LTUID_V2"),
    "ltoken_v2": os.getenv("LTOKEN_V2")
}