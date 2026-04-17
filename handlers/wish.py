import io
import random

from aiogram import Router, types
from aiogram.filters import Command
from aiogram.types import BufferedInputFile, FSInputFile
from aiogram.exceptions import TelegramBadRequest

from services.image_service import combine_images
from database.mongo import users_col

# IMPORT YOUR DATA
from assets.characters import characters5, characters4, weapons3, rare

router = Router()

CURRENT_RATE_UP_KEY = "flins"
CURRENT_RATE_UP_NAME = characters5.get(CURRENT_RATE_UP_KEY, "Flins")


# =========================
# 🔟 TEN WISH
# =========================
@router.message(Command("wish10"))
async def wish_cmd_10(message: types.Message):
    user_id = str(message.from_user.id)

    user = await users_col.find_one({"user_id": user_id})
    if not user:
        user = {
            "user_id": user_id,
            "pity": 0,
            "count4": 0,
            "total_wishes": 0,
            "wish_count": 200,
            "collection": {},
            "is_guaranteed": False
        }
        await users_col.insert_one(user)

    pity = user.get("pity", 0)
    count4 = user.get("count4", 0)
    wish_count = user.get("wish_count", 0)
    total_wishes = user.get("total_wishes", 0)
    collection = user.get("collection", {})
    is_guaranteed = user.get("is_guaranteed", False)

    if wish_count < 10:
        await message.answer(f"❌ You only have {wish_count} wishes.")
        return

    # Loading
    try:
        loading = FSInputFile("assets/images/Loading_Screen_Startup.webp")
        loading_msg = await message.answer_photo(loading, caption="✨ Invoking the Tides of Fate...")
    except:
        loading_msg = await message.answer("✨ Invoking the Tides of Fate...")

    results = []
    pulled = {}
    got_4_or_above = False

    splash_name = "Debate Club"
    splash_rarity = 3
    best_score = 0
    file_path = ""

    for i in range(10):
        pity += 1
        roll = random.randint(1, 1000)

        is_5 = False
        is_4 = False
        is_rare = False

        # ⭐ 5-star
        if pity >= 90:
            is_5 = True
            pity = 0
        elif roll <= 6:
            is_5 = True
            pity = 0

        # ⭐ 4-star guarantee
        elif count4 >= 9 or (i == 9 and not got_4_or_above):
            is_4 = True
            count4 = 0

        elif roll <= 60:
            is_4 = True
            count4 = 0

        # ⭐ rare
        elif roll <= 100:
            is_rare = True
            count4 += 1

        else:
            count4 += 1

        # =====================
        # RESULT HANDLING
        # =====================
        if is_5:
            got_4_or_above = True
            win = random.randint(1, 100)

            if is_guaranteed or win <= 50:
                key = CURRENT_RATE_UP_KEY
                name = CURRENT_RATE_UP_NAME
                is_guaranteed = False
                tag = "(RATE-UP WIN!)"
                score = 4
            else:
                key = random.choice(list(characters5.keys()))
                name = characters5[key]
                is_guaranteed = True
                tag = "(50/50 Lost...)"
                score = 2

            path = f"https://raw.githubusercontent.com/Mantan21/Genshin-Impact-Wish-Simulator/master/src/images/characters/splash-art/5star/{key}.webp"

            if score > best_score:
                splash_name = name
                splash_rarity = 5
                file_path = path
                best_score = score

            total = collection.get(name, 0) + pulled.get(name, 0)
            if total >= 7:
                wish_count += 2
                results.append(f"꩜ {name} (C6+ → +2 Wish) ★★★★★ {tag}")
            else:
                pulled[name] = pulled.get(name, 0) + 1
                results.append(f"꩜ {name} ★★★★★ {tag}")

        elif is_4:
            got_4_or_above = True

            key = random.choice(list(characters4.keys()))
            name = characters4[key]
            path = f"https://raw.githubusercontent.com/Mantan21/Genshin-Impact-Wish-Simulator/master/src/images/characters/splash-art/4star/{key}.webp"

            if best_score < 1:
                splash_name = name
                splash_rarity = 4
                file_path = path
                best_score = 1

            total = collection.get(name, 0) + pulled.get(name, 0)
            if total >= 7:
                wish_count += 1
                results.append(f"꩜ {name} (C6+ → +1 Wish) ★★★★")
            else:
                pulled[name] = pulled.get(name, 0) + 1
                results.append(f"꩜ {name} ★★★★")

        elif is_rare:
            key = random.choice(list(rare.keys()))
            name = rare[key]
            path = f"images/rare/{key}.webp"

            if best_score < 3:
                splash_name = name
                splash_rarity = 3
                file_path = path
                best_score = 3

            total = collection.get(name, 0) + pulled.get(name, 0)
            if total >= 7:
                wish_count += 1
                results.append(f"꩜ {name} (C6+ → +1 Wish) ✨")
            else:
                pulled[name] = pulled.get(name, 0) + 1
                results.append(f"꩜ {name} ✨")

        else:
            key = random.choice(list(weapons3.keys()))
            name = weapons3[key]
            results.append(f"꩜ {name} ★★★")

    # =====================
    # SAVE DATA
    # =====================
    total_wishes += 10
    wish_count -= 10

    update = {
        "$set": {
            "wish_count": wish_count,
            "pity": pity,
            "count4": count4,
            "total_wishes": total_wishes,
            "is_guaranteed": is_guaranteed
        }
    }

    if pulled:
        inc = {f"collection.{k}": v for k, v in pulled.items()}
        update["$inc"] = inc

    await users_col.update_one({"user_id": user_id}, update)

    # =====================
    # IMAGE
    # =====================
    bg = "https://raw.githubusercontent.com/Mantan21/Genshin-Impact-Wish-Simulator/master/src/images/background/splash-background.webp"

    img = await combine_images(file_path, bg, splash_name, splash_rarity)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)

    try:
        await loading_msg.delete()
    except TelegramBadRequest:
        pass

    await message.answer_photo(
        BufferedInputFile(buf.read(), "wish.png"),
        caption="★ Your 10-Pull Results ★\n\n" + "\n".join(results)
    )


# =========================
# 🎯 SINGLE WISH
# =========================
@router.message(Command("wish"))
async def wish_cmd(message: types.Message):
    if message.chat.type != "private":
        await message.reply("⚠️ Use this in private chat.")
        return

    user_id = str(message.from_user.id)
    user = await users_col.find_one({"user_id": user_id})

    if not user:
        user = {
            "user_id": user_id,
            "pity": 0,
            "count4": 0,
            "total_wishes": 0,
            "wish_count": 200,
            "collection": {},
            "is_guaranteed": False
        }
        await users_col.insert_one(user)

    pity = user.get("pity", 0)
    count4 = user.get("count4", 0)
    wish_count = user.get("wish_count", 0)
    total_wishes = user.get("total_wishes", 0)
    collection = user.get("collection", {})
    is_guaranteed = user.get("is_guaranteed", False)

    if wish_count < 1:
        await message.answer("❌ No wishes left.")
        return

    pity += 1
    roll = random.randint(1, 1000)

    is_5 = False
    is_4 = False

    if pity >= 90 or roll <= 6:
        is_5 = True
        pity = 0
        count4 = 0

    elif count4 >= 9 or roll <= 60:
        is_4 = True
        count4 = 0

    else:
        count4 += 1

    # RESULT
    if is_5:
        win = random.randint(1, 100)

        if is_guaranteed or win <= 50:
            key = CURRENT_RATE_UP_KEY
            name = CURRENT_RATE_UP_NAME
            is_guaranteed = False
            tag = "(RATE-UP WIN!)"
        else:
            key = random.choice(list(characters5.keys()))
            name = characters5[key]
            is_guaranteed = True
            tag = "(50/50 Lost...)"

        path = f"https://raw.githubusercontent.com/Mantan21/Genshin-Impact-Wish-Simulator/master/src/images/characters/splash-art/5star/{key}.webp"

        if collection.get(name, 0) >= 7:
            wish_count += 2
            text = f"{name} (C6+ → +2 Wish)"
        else:
            await users_col.update_one({"user_id": user_id}, {"$inc": {f"collection.{name}": 1}})
            text = name

        rarity = 5

    elif is_4:
        key = random.choice(list(characters4.keys()))
        name = characters4[key]
        path = f"https://raw.githubusercontent.com/Mantan21/Genshin-Impact-Wish-Simulator/master/src/images/characters/splash-art/4star/{key}.webp"

        if collection.get(name, 0) >= 7:
            wish_count += 1
            text = f"{name} (C6+ → +1 Wish)"
        else:
            await users_col.update_one({"user_id": user_id}, {"$inc": {f"collection.{name}": 1}})
            text = name

        rarity = 4
        tag = ""

    else:
        key = random.choice(list(weapons3.keys()))
        name = weapons3[key]
        path = f"https://raw.githubusercontent.com/FrenzyYum/GenshinWishingBot/master/assets/images/{key}.webp"
        text = name
        rarity = 3
        tag = ""

    wish_count -= 1
    total_wishes += 1

    await users_col.update_one(
        {"user_id": user_id},
        {"$set": {
            "wish_count": wish_count,
            "pity": pity,
            "count4": count4,
            "total_wishes": total_wishes,
            "is_guaranteed": is_guaranteed
        }}
    )

    bg = "https://raw.githubusercontent.com/Mantan21/Genshin-Impact-Wish-Simulator/master/src/images/background/splash-background.webp"

    img = await combine_images(path, bg, text, rarity)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)

    await message.answer_photo(
        BufferedInputFile(buf.read(), "wish.png"),
        caption=f"{text} {tag}"
    )