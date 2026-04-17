import io
import random
from aiogram import Router, types
from aiogram.filters import Command
from aiogram.types import BufferedInputFile, FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.exceptions import TelegramBadRequest

from services.image_service import combine_images
from database.mongo import users_col

# IMPORT YOUR DATA
from data.characters import characters5, characters4, weapons3, rare

router = Router()
ITEMS_PER_PAGE = 10
CURRENT_RATE_UP_KEY = "flins"
CURRENT_RATE_UP_NAME = characters5.get(CURRENT_RATE_UP_KEY, "Flins")
def get_rarity(name):
    clean_name = name.strip()
    if clean_name in characters5.values():
        return 5
    elif clean_name in characters4.values():
        return 4
    elif clean_name in rare.values():
        return 6
    else:
        return 3
@router.message(Command("stats"))
async def show_stats(message: types.Message):
    user_id = str(message.from_user.id)

    user = await users_col.find_one({"user_id": user_id})
    if not user:
        user = {"user_id": user_id, "pity": 0, "count4": 0, "total_wishes": 0 , "wish_count":200}
        await users_col.insert_one(user)
    wish_count = user["wish_count"]
    twishes = user["total_wishes"]
    pity = user["pity"]
    count4 = user["count4"]
    guaranteed = "✅ Yes" if user.get("is_guaranteed", False) else "❌ No"

    await message.reply(
        f"Stats for {message.from_user.first_name}:\n"
        f"Total wishes: {twishes}\n"
        f"Wishes: {wish_count}\n"
        f"🔥 Guaranteed: {guaranteed}\n"
        f"Current 5★ Pity: {pity}\n"
        f"Current 4★ Pity: {count4}"
    )

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
@router.message(Command("collection"))
async def show_collection(message: types.Message):
    user_id = str(message.from_user.id)
    user = await users_col.find_one({"user_id": user_id})

    if not user or "collection" not in user or not user["collection"]:
        await message.reply("Your collection is empty!\nUse /wish or /wish10 to find characters.")
        return

    chars = user["collection"]
    sorted_chars = sorted(
        chars.items(),
        key=lambda x: (get_rarity(x[0]), x[1]),
        reverse=True
    )

    text, keyboard = build_collection_page(
        sorted_chars,
        0,
        message.from_user.first_name,
        user_id
    )

    await message.reply(text, reply_markup=keyboard, parse_mode="Markdown")
def build_collection_page(sorted_chars, page, first_name, user_id):
    start = page * ITEMS_PER_PAGE
    end = start + ITEMS_PER_PAGE
    items = sorted_chars[start:end]

    response = f"𑣲 {first_name}'s Characters\n"
    response += "──── ⋆⋅☆⋅⋆ ────\n\n"

    for name, count in items:
        num = count - 1
        constellation = "C6+" if num > 6 else f"C{num}"
        rarity = get_rarity(name)
        stars = "✨" if rarity == 6 else "★" * rarity
        response += f"{stars} {name} — {constellation}\n"

    total_pages = (len(sorted_chars) - 1) // ITEMS_PER_PAGE
    buttons = []

    if page > 0:
        buttons.append(
            InlineKeyboardButton(text="Back", callback_data=f"col_{page-1}_{user_id}")
        )

    if page < total_pages:
        buttons.append(
            InlineKeyboardButton(text="Next", callback_data=f"col_{page+1}_{user_id}")
        )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[buttons]) if buttons else None
    return response, keyboard
async def add_to_collection(user_id, char_name):
    await users_col.update_one(
        {"user_id": user_id},
        {"$inc": {f"collection.{char_name}": 1}}
    )

@router.callback_query(lambda c: c.data.startswith("col_"))
async def change_collection_page(callback: types.CallbackQuery):
    data_parts = callback.data.split("_")
    page = int(data_parts[1])
    owner_id = data_parts[2]
    clicker_id = str(callback.from_user.id)

    if clicker_id != owner_id:
        await callback.answer("This is not your collection menu!", show_alert=True)
        return

    user = await users_col.find_one({"user_id": owner_id})
    if not user:
        return

    chars = user["collection"]
    sorted_chars = sorted(
        chars.items(),
        key=lambda x: (get_rarity(x[0]), x[1]),
        reverse=True
    )

    text, keyboard = build_collection_page(
        sorted_chars,
        page,
        callback.from_user.first_name,
        owner_id
    )

    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")