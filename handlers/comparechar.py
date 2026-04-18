import json
import asyncio
import os

from aiogram import Router, types, F
from aiogram.types import InputMediaPhoto, FSInputFile
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database.mongo import users_col
from services.get_enkadata import get_enkadata
from services.compare_card import compare_characters

router6 = Router()


# ==============================
# COMMAND
# ==============================
@router6.message(F.text.startswith("/comparechar"))
async def cmd_compare(message: types.Message):
    if not message.reply_to_message:
        return await message.reply("Please reply to a user's message to compare characters.")

    sender_data = await users_col.find_one({"user_id": str(message.from_user.id)})
    target_data = await users_col.find_one({"user_id": str(message.reply_to_message.from_user.id)})

    if not sender_data or not target_data:
        return await message.reply("Both users must be registered.")

    u1 = sender_data['genshin_uid']
    u2 = target_data['genshin_uid']
    owner_id = message.from_user.id

    await show_comparison_menu(message, u1, u2, owner_id)


# ==============================
# MENU
# ==============================
async def show_comparison_menu(event, u1, u2, owner_id, is_callback=False):

    if is_callback:
        await event.answer("Refreshing common characters...")
    else:
        temp_msg = await event.reply("Searching for common characters...")

    d1, d2 = await asyncio.gather(get_enkadata(u1), get_enkadata(u2))

    ids1 = {str(c['avatarId']) for c in d1.get("showAvatarInfoList", [])}
    ids2 = {str(c['avatarId']) for c in d2.get("showAvatarInfoList", [])}
    common = ids1.intersection(ids2)

    if not common:
        error_text = "❌ No common characters found in your showcases!"
        if not is_callback:
            await temp_msg.delete()
            return await event.reply(error_text)
        else:
            return await event.message.edit_text(error_text)

    builder = InlineKeyboardBuilder()

    with open('assets/json/char.json', 'r') as f:
        char_map = json.load(f)

    orig_msg_id = event.message.message_id if is_callback else event.message_id

    for cid in list(common)[:18]:
        name = char_map.get(str(cid), {}).get("name", f"ID: {cid}")
        builder.button(
            text=name,
            callback_data=f"comp:{u1}:{u2}:{cid}:{owner_id}:{orig_msg_id}"
        )

    builder.adjust(3)

    text = "<b>Character Comparison</b>\nSelect a common character to compare stats:"

    if is_callback:
        await event.message.delete()
        await event.message.answer(text, reply_markup=builder.as_markup(), parse_mode="HTML")
    else:
        await temp_msg.delete()
        await event.reply(text, reply_markup=builder.as_markup(), parse_mode="HTML")


# ==============================
# CALLBACK
# ==============================
@router6.callback_query(F.data.startswith("comp:"))
async def handle_comp(callback: types.CallbackQuery):
    data = callback.data.split(":")
    u1, u2, cid = data[1], data[2], data[3]
    owner_id = int(data[4])
    orig_msg_id = int(data[5])

    if callback.from_user.id != owner_id:
        return await callback.answer("This menu isn't for you!", show_alert=True)

    await callback.answer("Generating...")

    # ==============================
    # LOADING MESSAGE (FIXED)
    # ==============================
    loading_path = "assets/images/Loading_Screen_Startup.webp"

    if os.path.exists(loading_path):
        loading_msg = await callback.message.answer_photo(
            photo=FSInputFile(loading_path),
            caption="<b>Creating comparison card... Please wait.</b>",
            parse_mode="HTML"
        )
        is_photo = True
    else:
        loading_msg = await callback.message.answer(
            "<b>Creating comparison card... Please wait.</b>",
            parse_mode="HTML"
        )
        is_photo = False

    # delete menu to prevent spam clicks
    await callback.message.delete()

    # ==============================
    # PROCESS IMAGE
    # ==============================
    img_bytes = await compare_characters(int(u1), int(u2), int(cid))

    if img_bytes is None:
        if is_photo:
            return await loading_msg.edit_caption(
                caption="<b>❌ Error:</b> Failed to generate the comparison.",
                parse_mode="HTML"
            )
        else:
            return await loading_msg.edit_text(
                "<b>❌ Error:</b> Failed to generate the comparison.",
                parse_mode="HTML"
            )

    # ==============================
    # SEND RESULT
    # ==============================
    await callback.message.answer_photo(
        photo=types.BufferedInputFile(img_bytes.read(), filename="comparison.png"),
        caption="<b>Comparison Complete!</b>",
        parse_mode="HTML",
        reply_to_message_id=orig_msg_id
    )

    # ==============================
    # CLEANUP
    # ==============================
    await loading_msg.delete()