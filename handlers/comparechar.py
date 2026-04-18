import json
import asyncio
from aiogram import Router, types,F
from aiogram.types import InputMediaPhoto,FSInputFile
from aiogram.utils.keyboard import InlineKeyboardBuilder
from database.mongo import users_col
from services.get_enkadata import get_enkadata
from services.compare_card import compare_characters
router6 = Router()
@router6.message(F.text.startswith("/comparechar"))
async def cmd_compare(message: types.Message):
    if not message.reply_to_message:
        return await message.reply("Please reply to a user's message to compare characters.")

    sender_data = await users_col.find_one({"user_id": str(message.from_user.id)})
    target_data = await users_col.find_one({"user_id": str(message.reply_to_message.from_user.id)})

    if not sender_data or not target_data:
        return await message.reply("Both users must be registered.")

    u1, u2 = sender_data['genshin_uid'], target_data['genshin_uid']
    owner_id = message.from_user.id

    await show_comparison_menu(message, u1, u2, owner_id)
async def show_comparison_menu(event, u1, u2, owner_id, is_callback=False):
    """Helper function to show the character list (used by command and back button)"""

    if is_callback:
        await event.answer("Refreshing common characters...")
    else:
        temp_msg = await event.reply("Searching for common characters...")

    d1, d2 = await asyncio.gather(get_enkadata(u1), get_enkadata(u2))

    ids1 = {str(c['avatarId']) for c in d1.get("showAvatarInfoList", [])}
    ids2 = {str(c['avatarId']) for c in d2.get("showAvatarInfoList", [])}
    common = ids1.intersection(ids2)

    if not common:
        error_text = " No common characters found in your showcases!"
        if not is_callback: await temp_msg.delete()
        return await event.message.edit_text(error_text) if is_callback else await event.reply(error_text)

    builder = InlineKeyboardBuilder()
    with open('char.json', 'r') as f:
        char_map = json.load(f)
    orig_msg_id = event.message.message_id if is_callback else event.message_id
    for cid in list(common)[:18]:
        name = char_map.get(str(cid), {}).get("name", f"ID: {cid}")
        builder.button(text=name, callback_data=f"comp:{u1}:{u2}:{cid}:{owner_id}:{orig_msg_id}")

    builder.adjust(3)
    text = "<b>Character Comparison</b>\nSelect a common character to compare stats:"

    if is_callback:
        await event.message.delete()
        await event.message.answer(text, reply_markup=builder.as_markup(), parse_mode="HTML")
    else:
        await temp_msg.delete()
        await event.reply(text, reply_markup=builder.as_markup(), parse_mode="HTML")

@router6.callback_query(F.data.startswith("comp:"))
async def handle_comp(callback: types.CallbackQuery):
    data = callback.data.split(":")
    u1, u2, cid, owner_id, orig_msg_id = data[1], data[2], data[3], int(data[4]), int(data[5])

    if callback.from_user.id != owner_id:
        return await callback.answer("This menu isn't for you!", show_alert=True)

    await callback.answer()

    try:
        await callback.message.edit_media(
            media=InputMediaPhoto(
                media=FSInputFile("asstests/Loading_Screen_Startup.webp"),
                caption="<b>Creating comparison card... Please wait.</b>",
                parse_mode="HTML"
            )
        )
    except Exception:
        pass

    img_bytes = await compare_characters(int(u1), int(u2), int(cid))

    if img_bytes is None:
        await callback.message.edit_caption(
            caption="<b>❌ Error:</b> Failed to generate the comparison. This usually happens if Enka.network is lagging or profile details are hidden.",
            parse_mode="HTML"
        )
        return

    await callback.message.delete()
    await callback.message.answer_photo(
        photo=types.BufferedInputFile(img_bytes.read(), filename="comparison.png"),
        caption=f"<b>Comparison Complete!</b>",
        parse_mode="HTML",
        reply_to_message_id=orig_msg_id
    )
