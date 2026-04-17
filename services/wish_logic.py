import random
from database.mongo import users_col

from data.characters import characters5, characters4, weapons3

CURRENT_RATE_UP_NAME = "Raiden Shogun"
CURRENT_RATE_UP_KEY = "RaidenShogun"

BG_URL = "https://raw.githubusercontent.com/Mantan21/Genshin-Impact-Wish-Simulator/master/src/images/background/splash-background.webp"


async def get_user(user_id):
    user = await users_col.find_one({"user_id": str(user_id)})
    if not user:
        user = {
            "user_id": str(user_id),
            "pity": 0,
            "count4": 0,
            "wish_count": 200,
            "collection": {},
            "is_guaranteed": False
        }
        await users_col.insert_one(user)
    return user


async def save_user(user_id, data):
    await users_col.update_one(
        {"user_id": str(user_id)},
        {"$set": data}
    )


async def wish_single(user_id):
    user = await get_user(user_id)

    pity = user["pity"]
    count4 = user["count4"]
    wish_count = user["wish_count"]
    guaranteed = user.get("is_guaranteed", False)

    if wish_count < 1:
        return {"error": "Not enough wishes"}

    is_5 = False
    is_4 = False

    if pity >= 89:
        is_5 = True
    elif random.randint(1, 1000) < 7:
        is_5 = True
    elif count4 >= 9:
        is_4 = True

    name = ""
    rarity = 3
    img = ""
    result_msg = ""

    # ------------------------
    # 5 STAR LOGIC
    # ------------------------
    if is_5:
        pity = 0
        count4 += 1

        win_roll = random.randint(1, 100)

        # GUARANTEE SYSTEM (IMPORTANT FIX)
        if guaranteed:
            file_key = CURRENT_RATE_UP_KEY
            name = CURRENT_RATE_UP_NAME
            guaranteed = False
            result_msg = "(Guaranteed Rate-Up!)"

        elif win_roll <= 50:
            file_key = CURRENT_RATE_UP_KEY
            name = CURRENT_RATE_UP_NAME
            guaranteed = False
            result_msg = "(50/50 Won!)"

        else:
            file_key = random.choice(list(characters5.keys()))
            name = characters5[file_key]
            guaranteed = True
            result_msg = "(50/50 Lost...)"

        rarity = 5
        img = f"https://raw.githubusercontent.com/Mantan21/Genshin-Impact-Wish-Simulator/master/src/images/characters/splash-art/5star/{file_key}.webp"

    elif is_4:
        key = random.choice(list(characters4.keys()))
        name = characters4[key]
        rarity = 4
        img = f"https://raw.githubusercontent.com/Mantan21/Genshin-Impact-Wish-Simulator/master/src/images/characters/splash-art/4star/{key}.webp"
        count4 = 0

    else:
        key = random.choice(list(weapons3.keys()))
        name = weapons3[key]
        rarity = 3
        img = f"https://raw.githubusercontent.com/FrenzyYum/GenshinWishingBot/master/assets/images/{key}.webp"
        count4 += 1
        pity += 1

    wish_count -= 1

    await users_col.update_one(
        {"user_id": str(user_id)},
        {"$set": {
            "pity": pity,
            "count4": count4,
            "wish_count": wish_count,
            "is_guaranteed": guaranteed
        }}
    )

    return {
        "error": None,
        "name": name,
        "rarity": rarity,
        "image": img,
        "bg": BG_URL,
        "text": f"꩜ {name} ★{rarity} {result_msg}"
    }


async def wish_ten(user_id):
    results = []
    best = None

    for _ in range(10):
        res = await wish_single(user_id)

        if res.get("error"):
            continue

        results.append(res["text"])

        if not best or res["rarity"] > best["rarity"]:
            best = res

    return {
        "error": None,
        "name": best["name"],
        "rarity": best["rarity"],
        "image": best["image"],
        "bg": best["bg"],
        "text": "\n".join(results)
    }