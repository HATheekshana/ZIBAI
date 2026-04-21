import os
import genshin
from dotenv import load_dotenv
from aiogram import Router, types ,F
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import FSInputFile, InputMediaPhoto


from aiogram.filters import Command

from config import ADMIN_ID
from services.banner import get_banner_text, CURRENT_IMAGES, NEXT_IMAGES
from database.mongo import users_col
from dotenv import load_dotenv

router5 = Router()
load_dotenv()

cookies = {
    "ltuid_v2": os.getenv("LTUID_V2"),
    "ltoken_v2": os.getenv("LTOKEN_V2")
}

# ✅ Global client (better than creating every time)
client = genshin.Client(cookies, region=genshin.Region.OVERSEAS)


# =========================
# 📊 FETCH ABYSS DATA
# =========================
async def get_abyss_data(uid: str):
    return await client.get_spiral_abyss(uid)


# =========================
# 🧾 FORMAT DATA
# =========================
async def format_abyss_info(abyss_data):
    season = abyss_data.season
    res = f"⸸ SPIRAL ABYSS S{season} ⸸\n\n"

    for floor in sorted(abyss_data.floors, key=lambda x: x.floor):
        if floor.floor < 11:
            continue

        res += f"ꫂ❁ FLOOR {floor.floor}】\n"

        for chamber in floor.chambers:
            stars = "✮" * chamber.stars + "☆" * (3 - chamber.stars)
            res += f"⧽ Chamber {chamber.chamber} - {stars}\n"

        res += "╰➤─── ⋆⋅⸸⋅⋆ ──────\n\n"

    rank = abyss_data.ranks

    res += f"✎ Deepest Descent: {abyss_data.max_floor}\n"
    res += f"✎ Total Stars: {abyss_data.total_stars}\n"
    res += f"✎ Total Battles: {abyss_data.total_battles}\n\n"

    def get_rank_str(possible_attrs):
        for attr in possible_attrs:
            val = getattr(rank, attr, None)
            if val and isinstance(val, list) and len(val) > 0:
                return f"{val[0].value} ({val[0].name})"
        return "N/A"

    res += f"✎ Most Kills: {get_rank_str(['most_kills'])}\n"
    res += f"✎ Strongest Strike: {get_rank_str(['strongest_strike'])}\n"
    res += f"✎ Most Damage Taken: {get_rank_str(['take_damage', 'max_damage_taken', 'most_damage_taken'])}\n"
    res += f"✎ Most Bursts: {get_rank_str(['most_bursts', 'most_bursts_used'])}\n"
    res += f"✎ Most Skills: {get_rank_str(['most_skills', 'most_skills_used'])}\n"

    return res


# =========================
# 🎯 COMMAND
# =========================
@router5.message(Command("abyssinfo"))
async def abyss_info_command(message: types.Message):
    user_data = await users_col.find_one({"user_id": str(message.from_user.id)})

    if not user_data or "genshin_uid" not in user_data:
        return await message.answer("❌ Please use /login <uid> first.")

    uid = str(user_data["genshin_uid"]).strip()

    status_msg = await message.reply("⏳ Fetching Abyss data from HoYoLAB...")

    try:
        abyss = await get_abyss_data(uid)
        formatted_text = await format_abyss_info(abyss)

        await status_msg.edit_text(formatted_text)

    except genshin.errors.DataNotPublic:
        await status_msg.edit_text(
            "❌ Your Abyss stats are private.\nEnable 'Public' in HoYoLAB settings."
        )

    except genshin.errors.InvalidCookies:
        await status_msg.edit_text(
            "❌ Invalid HoYoLAB cookies. Please check your .env file."
        )

    except Exception as e:
        import traceback
        traceback.print_exc()

        await status_msg.edit_text(
            f"❌ Error fetching Abyss data:\n{str(e)}"
        )
from aiogram import Bot


@router5.message(Command("info"))
async def group_info(message: types.Message, bot: Bot):
    if message.from_user.id != ADMIN_ID:
        await message.answer("🚫 **Access Denied**")
        return
    args = message.text.split()

    if len(args) < 2:
        return await message.reply("Usage: /info <group_id>")

    group_id = args[1]

    try:
        chat = await bot.get_chat(group_id)

        await message.reply(
            f"🏷 Group Info\n\n"
            f"Name: {chat.title}\n"
            f"ID: {chat.id}\n"
            f"Type: {chat.type}"
        )

    except Exception as e:
        await message.reply(f"❌ Failed to fetch group info.\nError: {e}")
def get_banner_keyboard(mode="current", char_index=0):
    builder = InlineKeyboardBuilder()

    next_char = 1 if char_index == 0 else 0
    char_label = "View 2nd Character" if char_index == 0 else "View 1st Character"
    builder.row(types.InlineKeyboardButton(text=char_label, callback_data=f"swap:{mode}:{next_char}"))

    other_mode = "next" if mode == "current" else "current"
    mode_label = "Upcoming Banners" if mode == "current" else "Current Banners"
    builder.row(types.InlineKeyboardButton(text=mode_label, callback_data=f"swap:{other_mode}:0"))

    return builder.as_markup()

@router5.message(Command("banner"))
async def cmd_banner(message: types.Message):
    if not os.path.exists(CURRENT_IMAGES[0]):
        return await message.reply("❌ Banner image not found on server.")

    await message.reply_photo(
        photo=FSInputFile(CURRENT_IMAGES[0]),
        caption=get_banner_text("current"),
        reply_markup=get_banner_keyboard("current", 0),
        parse_mode="HTML"
    )

@router5.callback_query(F.data.startswith("swap:"))
async def handle_banner_swap(callback: types.CallbackQuery):
    _, mode, index = callback.data.split(":")
    index = int(index)

    image_list = CURRENT_IMAGES if mode == "current" else NEXT_IMAGES

    if not os.path.exists(image_list[index]):
        return await callback.answer("❌ Image file missing!", show_alert=True)

    await callback.message.edit_media(
        media=InputMediaPhoto(
            media=FSInputFile(image_list[index]),
            caption=get_banner_text(mode),
            parse_mode="HTML"
        ),
        reply_markup=get_banner_keyboard(mode, index)
    )
    await callback.answer()