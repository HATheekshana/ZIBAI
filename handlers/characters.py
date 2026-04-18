import json
import aiohttp
from aiogram import Router, types,F
from aiogram.filters import Command
from aiogram.types import BufferedInputFile,InputMediaPhoto
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.exceptions import TelegramBadRequest
from database.mongo import users_col
from services.get_enkadata import get_enkadata
from services.char_card import characters_card
from services.profile_card import create_genshin_profile
router2 = Router()
try:
    with open("char.json", "r", encoding="utf-8") as f:
        CHARACTER_MAP = json.load(f)
except FileNotFoundError:
    print("Warning: char.json not found")
    CHARCTER_MAP = {}
@router2.message(Command("characters"))
async def cmd_characters(message: types.Message):
    user_data = await users_col.find_one({"user_id": str(message.from_user.id)})

    if not user_data or "genshin_uid" not in user_data:
        return await message.reply("Please /login <uid> first.")

    db_uid = str(user_data["genshin_uid"]).strip()
    msg = await message.reply("Fetching your showcase...")

    try:
        user_info_enka = await get_enkadata(db_uid)
        showcase_items = user_info_enka.get("showAvatarInfoList", [])
    except Exception as e:
        print(f"Enka Fetch Error: {e}")
        return await msg.edit_text("Failed to reach Enka.network. Try again later.")

    if not showcase_items:
        return await msg.edit_text(
            "No characters found!\nMake sure 'Show Character Details' is enabled in your profile."
        )

    builder = InlineKeyboardBuilder()
    for index, char in enumerate(showcase_items):
        char_id = str(char.get("avatarId"))
        char_entry = CHARACTER_MAP.get(char_id)
        display_name = char_entry.get("name", "Unknown") if char_entry else f"ID: {char_id}"

        builder.button(
            text=display_name,
            callback_data=f"gen_{db_uid}_{index}_{message.from_user.id}"
        )
    builder.adjust(3)

    try:
        image_buffer = await create_genshin_profile(db_uid)

        if not image_buffer:
            raise Exception("Empty buffer returned")

    except Exception as e:
        print(f"Profile Gen Error: {e}")
        return await msg.edit_text("❌ Failed to generate profile image.")

    photo = BufferedInputFile(image_buffer.getvalue(), filename=f"{db_uid}.png")

    try:
        await msg.delete()
    except TelegramBadRequest:
        pass

    await message.reply_photo(
        photo=photo,
        caption="✨ <b>Character Showcase</b>\nSelect a character to see detailed stats:",parse_mode="HTML",
        reply_markup=builder.as_markup()
    )

@router2.callback_query(F.data.startswith("gen_"))
async def handle_card_generation(callback: types.CallbackQuery):
    parts = callback.data.split("_")
    uid, char_index, owner_id = parts[1], int(parts[2]), int(parts[3])

    if callback.from_user.id != owner_id:
        return await callback.answer("⏳ This menu isn't for you!", show_alert=True)

    await callback.answer("⏳ Generating your character card...")

    user_info = await get_enkadata(uid)
    showcase = user_info.get("showAvatarInfoList", [])

    if char_index >= len(showcase):
        return await callback.answer("❌ Character no longer in showcase.", show_alert=True)

    current_char = showcase[char_index]
    char_id = int(current_char.get("avatarId"))

    try:
        image_buffer = await characters_card(uid, char_id, owner_id)

        if not image_buffer:
            raise Exception("Image generation returned empty buffer")

    except Exception as e:
        print(f"LOCAL GEN ERROR: {e}")
        return await callback.message.edit_caption(
            caption="❌ Failed to generate character card. Please try again later."
        )

    ranking_text = ""

    ranking_api = f"https://test-xehj.onrender.com/get/ranking/{uid}"
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(ranking_api, timeout=2) as rank_resp:
                if rank_resp.status == 200:
                    all_ranks = await rank_resp.json()
                    char_rank_data = all_ranks.get(str(char_id))
                    if char_rank_data:
                        rank = char_rank_data.get("ranking")
                        out_of = char_rank_data.get("outOf")
                        percent = char_rank_data.get("percent")
                        ranking_text = (
                            f"\n\n<b>ʚଓ Global Rank :</b> {rank}/{out_of}"
                            f"\n<b>ʚଓ Top :</b> {percent}%"
                        )
        except Exception as e:
            print(f"Ranking API Error: {e}")
    char_entry = CHARACTER_MAP.get(str(char_id), {})
    display_name = char_entry.get("name", "Unknown Character")

    back_builder = InlineKeyboardBuilder()
    back_builder.button(text="Back to List", callback_data=f"refresh_{uid}_{owner_id}")

    photo = BufferedInputFile(image_buffer.getvalue(), filename=f"{char_id}_{uid}.png")

    try:
        await callback.message.delete()
    except TelegramBadRequest:
        pass

    target = callback.message.reply_to_message or callback.message

    await target.reply_photo(
        photo=photo,
        caption=f"<b>{display_name}</b>{ranking_text}",
        reply_markup=back_builder.as_markup(),
        parse_mode="HTML"
    )
@router2.callback_query(F.data.startswith("refresh_"))
async def handle_back_button(callback: types.CallbackQuery):
    parts = callback.data.split("_")
    uid, owner_id = parts[1], int(parts[2])

    if callback.from_user.id != owner_id:
        return await callback.answer("❌ You can't use this button.", show_alert=True)

    user_info = await get_enkadata(uid)
    showcase = user_info.get("showAvatarInfoList", [])

    builder = InlineKeyboardBuilder()

    for index, char in enumerate(showcase):
        char_id = str(char.get("avatarId"))
        name = CHARACTER_MAP.get(char_id, {}).get("name", f"ID: {char_id}")

        builder.button(
            text=name,
            callback_data=f"gen_{uid}_{index}_{owner_id}"
        )

    builder.adjust(3)

    image_buffer = await create_genshin_profile(uid)

    if not image_buffer:
        return await callback.answer("❌ Failed to reload.", show_alert=True)

    photo = BufferedInputFile(image_buffer.getvalue(), filename=f"{uid}.png")

    await callback.message.edit_media(
        media=InputMediaPhoto(
            media=photo,
            caption="<b>Character Showcase</b>\nSelect a character:",
            parse_mode="HTML"
        ),
        reply_markup=builder.as_markup()
    )