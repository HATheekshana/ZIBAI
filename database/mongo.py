from motor.motor_asyncio import AsyncIOMotorClient
from config import MONGO_URL

client = AsyncIOMotorClient(MONGO_URL)
db = client["genshin_bot"]

users_col = db["user_stats"]
groups_col = db["groups"]