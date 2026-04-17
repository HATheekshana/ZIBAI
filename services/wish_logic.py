import random
import re
from database.mongo import users_col
from data.characters import characters5, characters4, weapons3

CURRENT_RATE_UP_NAME = "Raiden Shogun"
CURRENT_RATE_UP_KEY = "raiden-shogun" # Ensure this is hyphenated lowercase

def format_key(key):
    """Converts 'RaidenShogun' to 'raiden-shogun' for GitHub URLs."""
    return re.sub(r'(?<!^)(?=[A-Z])', '-', key).replace('_', '-').lower()

async def wish_single(user_id: str):
    user = await users_col.find_one({"user_id": str(user_id)})
    if not user:
        user = {"user_id": str(user_id), "pity": 0, "count4": 0, "wish_count": 200, "collection": {}, "is_guaranteed": False}
        await users_col.insert_one(user)

    pity = user.get("pity", 0) + 1
    count4 = user.get("count4", 0) + 1
    guaranteed = user.get("is_guaranteed", False)
    wish_count = user.get("wish_count", 0)

    if wish_count < 1: return {"error": "No Wishes Left!"}

    res = {"rarity": 3, "name": "", "key": "", "msg": ""}

    # 5-Star Logic (with 50/50)
    if pity >= 90 or random.randint(1, 1000) <= 6:
        res["rarity"], pity = 5, 0
        if guaranteed or random.random() <= 0.5:
            res["key"], res["name"] = CURRENT_RATE_UP_KEY, CURRENT_RATE_UP_NAME
            guaranteed = False
            res["msg"] = "✨ (RATE-UP WIN!)"
        else:
            res["key"] = random.choice(list(characters5.keys()))
            res["name"] = characters5[res["key"]]
            guaranteed = True
            res["msg"] = "💀 (50/50 Lost...)"
            
    # 4-Star Logic
    elif count4 >= 10 or random.randint(1, 100) <= 10:
        res["rarity"], count4 = 4, 0
        res["key"] = random.choice(list(characters4.keys()))
        res["name"] = characters4[res["key"]]
    else:
        res["key"] = random.choice(list(weapons3.keys()))
        res["name"] = weapons3[res["key"]]

    # Handle Database Updates
    wish_count -= 1
    await users_col.update_one({"user_id": str(user_id)}, {
        "$set": {"pity": pity, "count4": count4, "wish_count": wish_count, "is_guaranteed": guaranteed},
        "$inc": {f"collection.{res['name']}": 1}
    })

    # URL Construction (The Fix)
    f_key = format_key(res["key"])
    base = "https://raw.githubusercontent.com/Mantan21/Genshin-Impact-Wish-Simulator/master/src/images/characters/splash-art/"
    
    if res["rarity"] == 5:
        url = f"{base}5star/{f_key}.webp"
    elif res["rarity"] == 4:
        url = f"{base}4star/{f_key}.webp"
    else:
        url = f"https://raw.githubusercontent.com/FrenzyYum/GenshinWishingBot/master/assets/images/{res['key']}.webp"

    return {"name": res["name"], "rarity": res["rarity"], "url": url, "msg": res["msg"]}