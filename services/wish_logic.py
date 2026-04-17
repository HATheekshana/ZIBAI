import random
from database.mongo import users_col
from data.characters import characters5, characters4, weapons3

CURRENT_RATE_UP_NAME = "Raiden Shogun"
CURRENT_RATE_UP_KEY = "RaidenShogun"

async def wish_single(user_id: str):
    user = await users_col.find_one({"user_id": str(user_id)})
    if not user:
        user = {"user_id": str(user_id), "pity": 0, "count4": 0, "wish_count": 200, "collection": {}, "is_guaranteed": False}
        await users_col.insert_one(user)

    if user.get("wish_count", 0) < 1:
        return {"error": "Not enough wishes"}

    pity, count4 = user.get("pity", 0) + 1, user.get("count4", 0) + 1
    guaranteed = user.get("is_guaranteed", False)
    
    res = {"rarity": 3, "name": "", "key": "", "msg": ""}

    if pity >= 90 or random.randint(1, 1000) <= 6:
        res["rarity"], pity = 5, 0
        if guaranteed or random.random() <= 0.5:
            res["key"], res["name"], guaranteed = CURRENT_RATE_UP_KEY, CURRENT_RATE_UP_NAME, False
            res["msg"] = "(RATE-UP WIN!)"
        else:
            res["key"] = random.choice(list(characters5.keys()))
            res["name"], guaranteed = characters5[res["key"]], True
            res["msg"] = "(50/50 Lost...)"
    elif count4 >= 10 or random.randint(1, 100) <= 10:
        res["rarity"], count4, res["key"] = 4, 0, random.choice(list(characters4.keys()))
        res["name"] = characters4[res["key"]]
    else:
        res["key"] = random.choice(list(weapons3.keys()))
        res["name"] = weapons3[res["key"]]

    # Refund Logic
    wish_count = user["wish_count"] - 1
    owned = user.get("collection", {}).get(res["name"], 0)
    if owned >= 7:
        wish_count += (2 if res["rarity"] == 5 else 1)

    await users_col.update_one({"user_id": str(user_id)}, {
        "$set": {"pity": pity, "count4": count4, "wish_count": wish_count, "is_guaranteed": guaranteed},
        "$inc": {f"collection.{res['name']}": 1}
    })

    # Build URLs
    base = "https://raw.githubusercontent.com/Mantan21/Genshin-Impact-Wish-Simulator/master/src/images/characters/splash-art/"
    if res["rarity"] == 5: url = f"{base}5star/{res['key']}.webp"
    elif res["rarity"] == 4: url = f"{base}4star/{res['key']}.webp"
    else: url = f"https://raw.githubusercontent.com/FrenzyYum/GenshinWishingBot/master/assets/images/{res['key']}.webp"

    return {"name": res["name"], "rarity": res["rarity"], "url": url, "msg": res["msg"]}