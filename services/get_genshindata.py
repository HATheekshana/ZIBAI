import genshin
from dotenv import load_dotenv
import os

load_dotenv()
COOKIES = {
    "ltuid_v2": os.getenv("LTUID_V2"),
    "ltoken_v2": os.getenv("LTOKEN_V2")
}
client = genshin.Client(COOKIES)
client.region = genshin.Region.OVERSEAS
def calculate_world_level(ar):
    ar = int(ar)
    if ar < 20: return 0
    if ar < 25: return 1
    if ar < 30: return 2
    if ar < 35: return 3
    if ar < 40: return 4
    if ar < 45: return 5
    if ar < 50: return 6
    if ar < 55: return 7
    return 8
async def get_player_full_data(uid):
    raw_data = await client.get_genshin_user(uid)
    data = raw_data.dict()

    return {
        "nickname": data.get("info", {}).get("nickname", "Unknown"),
        "level": data.get("info", {}).get("level", 0),
        "world_level": calculate_world_level(data.get("info", {}).get("level", 0)),
        "achievements": data.get("stats", {}).get("achievements", 0),
        "days_active": data.get("stats", {}).get("days_active", 0),
        "luxurious": data.get("stats", {}).get("luxurious_chests", 0),
        "precious": data.get("stats", {}).get("precious_chests", 0),
        "exquisite": data.get("stats", {}).get("exquisite_chests", 0),
        "common": data.get("stats", {}).get("common_chests", 0),
        "in_game_avatar": data.get("info", {}).get("in_game_avatar", "Unknown"),
        "spiral_abyss": data.get("stats", {}).get("spiral_abyss", "Unknown"),
        "characters": data.get("characters", [])
    }