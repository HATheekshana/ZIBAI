import random
from database.mongo import users_col
from data.characters import characters5, characters4, weapons3

CURRENT_RATE_UP_NAME = "Raiden Shogun"
CURRENT_RATE_UP_KEY = "RaidenShogun"

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


async def wish_single(user_id):
    user = await get_user(user_id)

    pity = user["pity"]
    count4 = user["count4"]
    wish_count = user["wish_count"]
    guaranteed = user.get("is_guaranteed", False)

    if wish_count < 1:
        return {"error": "Not enough wishes"}

    is_5 = pity >= 89 or random.randint(1, 1000) < 7
    is_4 = count4 >= 9

    name = ""
    rarity = 3
    file_key = ""

    if is_5:
        pity = 0
        count4 += 1

        if guaranteed:
            file_key = CURRENT_RATE_UP_KEY
            name = CURRENT_RATE_UP_NAME
            guaranteed = False
        elif random.randint(1, 100) <= 50:
            file_key = CURRENT_RATE_UP_KEY
            name = CURRENT_RATE_UP_NAME
        else:
            file_key = random.choice(list(characters5.keys()))
            name = characters5[file_key]
            guaranteed = True

        rarity = 5

    elif is_4:
        file_key = random.choice(list(characters4.keys()))
        name = characters4[file_key]
        rarity = 4
        count4 = 0

    else:
        file_key = random.choice(list(weapons3.keys()))
        name = weapons3[file_key]
        rarity = 3
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

    img_url = f"{file_key}"  # THIS WILL MAP TO CACHE KEY

    return {
        "error": None,
        "name": name,
        "rarity": rarity,
        "image": img_url,
        "text": f"꩜ {name} ★{rarity}"
    }


async def wish_ten(user_id):
    results = []
    best = None

    for _ in range(10):
        res = await wish_single(user_id)
        if res["error"]:
            continue

        results.append(res["text"])

        if not best or res["rarity"] > best["rarity"]:
            best = res

    return {
        "name": best["name"],
        "rarity": best["rarity"],
        "image": best["image"],
        "text": "\n".join(results)
    }