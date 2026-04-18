from aiogram.fsm.state import State, StatesGroup
import json
import os
from io import BytesIO
from aiogram.fsm.context import FSMContext
from PIL import Image
from aiogram import Router, types,F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from database.mongo import users_col
from services.get_enkadata import get_enkadata
from dotenv import load_dotenv

load_dotenv()
ADMIN_VAL = os.getenv("ADMIN_ID")

ADMIN_ID = int(ADMIN_VAL)
router3 = Router()
try:
    with open("assets/json/char.json", "r", encoding="utf-8") as f:
        CHARACTER_MAP = json.load(f)
except FileNotFoundError:
    print("Warning: char.json not found")
    CHARCTER_MAP = {}
class CardSettings(StatesGroup):
    waiting_for_sticker = State()
    waiting_for_splash = State()

async def get_user_card_settings(user_id):
    user = await users_col.find_one({"user_id": str(user_id)})
    if not user or "card_settings" not in user:
        return {"graph_on": True, "disabled_graphs": [], "stickers": {}}
    return user["card_settings"]

router3.message(Command("settings"), F.chat.type == "private")
async def cmd_settings(message: types.Message):
    builder = InlineKeyboardBuilder()
    builder.button(text="🎴 Character Card", callback_data="set_card_menu")
    await message.answer("⚙️ <b>Bot Settings</b>", parse_mode="HTML", reply_markup=builder.as_markup())

router3.callback_query(F.data == "set_card_menu")
async def card_settings_menu(callback: types.CallbackQuery):
    settings = await get_user_card_settings(callback.from_user.id)

    builder = InlineKeyboardBuilder()
    builder.button(text="🖼 Manage Custom Stickers", callback_data="setup_sticker_start")
    builder.button(text="🌅 Manage Custom Splash Arts", callback_data="setup_splash_start")

    graph_status = "ON" if settings.get("graph_on", True) else "OFF"
    builder.button(text=f"Global Graph: {graph_status}", callback_data="toggle_graph_stat")

    if settings.get("disabled_graphs"):
        builder.button(text="🔄 Reset All Chars to ON", callback_data="reset_all_graphs")

    builder.adjust(1)
    builder.row(types.InlineKeyboardButton(text="⬅️ Back", callback_data="main_settings_menu"))
    await callback.message.edit_text("🎴 <b>Character Card Settings</b>\n\nTurning Global Graph OFF will hide radar charts for all characters.",
                                    parse_mode="HTML", reply_markup=builder.as_markup())

router3.callback_query(F.data == "toggle_graph_stat")
async def toggle_global_graph(callback: types.CallbackQuery):
    settings = await get_user_card_settings(callback.from_user.id)
    new_stat = not settings.get("graph_on", True)

    await users_col.update_one(
        {"user_id": str(callback.from_user.id)},
        {"$set": {"card_settings.graph_on": new_stat}},
        upsert=True
    )
    await callback.answer(f"Global Graph: {'ON' if new_stat else 'OFF'}")
    await card_settings_menu(callback)

router3.callback_query(F.data == "main_settings_menu")
async def main_settings_menu(callback: types.CallbackQuery):
    builder = InlineKeyboardBuilder()
    builder.button(text="🎴 Character Card", callback_data="set_card_menu")
    await callback.message.edit_text("⚙️ <b>Bot Settings</b>", parse_mode="HTML", reply_markup=builder.as_markup())

router3.callback_query(F.data == "reset_all_graphs")
async def reset_all_graphs(callback: types.CallbackQuery):
    await users_col.update_one(
        {"user_id": str(callback.from_user.id)},
        {"$set": {"card_settings.disabled_graphs": []}}
    )
    await callback.answer("All character-specific graphs reset to ON.")
    await card_settings_menu(callback)

router3.callback_query(F.data == "setup_sticker_start")
async def start_sticker_process(callback: types.CallbackQuery):
    user_data = await users_col.find_one({"user_id": str(callback.from_user.id)})
    if not user_data or "genshin_uid" not in user_data:
        return await callback.answer("❌ Please /login <uid> first.", show_alert=True)

    db_uid = str(user_data["genshin_uid"]).strip()
    user_info_enka = await get_enkadata(db_uid)
    showcase_items = user_info_enka.get("showAvatarInfoList", [])

    if not showcase_items:
        return await callback.message.edit_text("No characters found! Enable 'Show Character Details' in-game.")

    builder = InlineKeyboardBuilder()
    for char in showcase_items:
        char_id = str(char.get("avatarId"))
        char_entry = CHARACTER_MAP.get(char_id, {})
        display_name = char_entry.get("name", f"ID: {char_id}")
        builder.button(text=display_name, callback_data=f"pick_char_{char_id}")

    builder.adjust(3)
    builder.row(types.InlineKeyboardButton(text="⬅️ Back", callback_data="set_card_menu"))
    await callback.message.edit_text("✨ <b>Select a character to customize:</b>", parse_mode="HTML", reply_markup=builder.as_markup())

router3.callback_query(F.data == "setup_splash_start")
async def start_splash_process(callback: types.CallbackQuery):
    user_data = await users_col.find_one({"user_id": str(callback.from_user.id)})
    if not user_data or "genshin_uid" not in user_data:
        return await callback.answer("❌ Please /login <uid> first.", show_alert=True)

    db_uid = str(user_data["genshin_uid"]).strip()
    user_info_enka = await get_enkadata(db_uid)
    showcase_items = user_info_enka.get("showAvatarInfoList", [])

    if not showcase_items:
        return await callback.message.edit_text("No characters found! Enable 'Show Character Details' in-game.")

    builder = InlineKeyboardBuilder()
    for char in showcase_items:
        char_id = str(char.get("avatarId"))
        char_entry = CHARACTER_MAP.get(char_id, {})
        display_name = char_entry.get("name", f"ID: {char_id}")
        builder.button(text=display_name, callback_data=f"pick_char_splash_{char_id}")

    builder.adjust(3)
    builder.row(types.InlineKeyboardButton(text="⬅️ Back", callback_data="set_card_menu"))
    await callback.message.edit_text("🌅 <b>Select a character for custom splash art:</b>", parse_mode="HTML", reply_markup=builder.as_markup())

router3.callback_query(lambda c: c.data and c.data.startswith("pick_char_") and not c.data.startswith("pick_char_splash_"))
async def process_character_pick(callback: types.CallbackQuery, state: FSMContext):
    if state is not None:
        await state.clear()

    char_id = callback.data.split("_")[2]
    settings = await get_user_card_settings(callback.from_user.id)

    disabled_list = settings.get("disabled_graphs", [])
    is_disabled = char_id in disabled_list
    char_name = CHARACTER_MAP.get(char_id, {}).get("name", f"ID: {char_id}")

    builder = InlineKeyboardBuilder()
    status_text = "📊 Graph: OFF (Click to ON)" if is_disabled else "📊 Graph: ON (Click to OFF)"
    builder.button(text=status_text, callback_data=f"toggle_char_graph_{char_id}")
    builder.button(text="🖼 Set Custom Sticker", callback_data=f"set_sticker_{char_id}")
    
    builder.adjust(1)
    builder.row(types.InlineKeyboardButton(text="⬅️ Back", callback_data="setup_sticker_start"))

    await callback.message.edit_text(f"Settings for <b>{char_name}</b>:", parse_mode="HTML", reply_markup=builder.as_markup())

router3.callback_query(F.data.startswith("pick_char_splash_"))
async def process_character_pick_splash(callback: types.CallbackQuery, state: FSMContext):
    if state is not None:
        await state.clear()

    char_id = callback.data.split("_")[3]
    settings = await get_user_card_settings(callback.from_user.id)

    char_name = CHARACTER_MAP.get(char_id, {}).get("name", f"ID: {char_id}")

    builder = InlineKeyboardBuilder()
    builder.button(text="🌅 Set Custom Splash Art", callback_data=f"set_splash_{char_id}")
    
    splash_dict = settings.get("splash_arts", {})
    if char_id in splash_dict:
        builder.button(text="🔄 Reset Custom Splash Art", callback_data=f"reset_splash_{char_id}")
    
    builder.adjust(1)
    builder.row(types.InlineKeyboardButton(text="⬅️ Back", callback_data="setup_splash_start"))

    await callback.message.edit_text(f"🌅 <b>Custom Splash Art: {char_name}</b>", parse_mode="HTML", reply_markup=builder.as_markup())

router3.callback_query(F.data.startswith("toggle_char_graph_"))
async def toggle_specific_graph(callback: types.CallbackQuery):
    char_id = callback.data.split("_")[3]
    settings = await get_user_card_settings(callback.from_user.id)
    disabled_list = settings.get("disabled_graphs", [])

    if char_id in disabled_list:
        disabled_list.remove(char_id)
        msg = "Graph enabled for this character!"
    else:
        disabled_list.append(char_id)
        msg = "Graph disabled for this character!"

    await users_col.update_one(
        {"user_id": str(callback.from_user.id)},
        {"$set": {"card_settings.disabled_graphs": disabled_list}},
        upsert=True
    )
    await callback.answer(msg)
    await process_character_pick(callback, None)

router3.callback_query(F.data.startswith("set_sticker_"))
async def start_sticker_upload_prompt(callback: types.CallbackQuery, state: FSMContext):
    char_id = callback.data.split("_")[2]
    char_name = CHARACTER_MAP.get(char_id, {}).get("name", f"ID: {char_id}")

    await state.update_data(selected_char_id=char_id, prompt_message_id=callback.message.message_id)
    await state.set_state(CardSettings.waiting_for_sticker)

    await callback.message.edit_text(
        f"✨ <b>Custom Sticker: {char_name}</b>\n\nPlease send the <b>Sticker</b>, <b>Photo</b>, or <b>Image Document</b>.\n"
        "<i>Note: Stickers will prioritize this character if Graph is OFF.</i>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardBuilder().button(text="❌ Cancel", callback_data=f"pick_char_{char_id}").as_markup()
    )

router3.callback_query(F.data.startswith("set_splash_"))
async def start_splash_upload_prompt(callback: types.CallbackQuery, state: FSMContext):
    char_id = callback.data.split("_")[2]
    char_name = CHARACTER_MAP.get(char_id, {}).get("name", f"ID: {char_id}")

    await state.update_data(selected_char_id=char_id, prompt_message_id=callback.message.message_id)
    await state.set_state(CardSettings.waiting_for_splash)

    await callback.message.edit_text(
        f"🌅 <b>Custom Splash Art: {char_name}</b>\n\nPlease send the <b>Photo</b> or <b>Image Document</b>.\n"
        "<i>Note: This will replace the default splash art background.</i>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardBuilder().button(text="❌ Cancel", callback_data=f"pick_char_splash_{char_id}").as_markup()
    )

router3.message(CardSettings.waiting_for_sticker)
async def handle_sticker_upload(message: types.Message, state: FSMContext):
    data = await state.get_data()
    char_id_str = str(data.get("selected_char_id"))
    user_id = message.from_user.id

    if message.sticker:
        file = message.sticker
    elif message.photo:
        file = message.photo[-1]
    elif message.document and message.document.mime_type.startswith("image/"):
        file = message.document
    else:
        return await message.answer("❌ Please send a valid Image, Sticker, or Photo.")

    if file.file_size > 500 * 1024:
        return await message.answer("❌ File too large! Please keep it under 500KB.")

    relative_dir = "custom_assets/stickers"
    abs_dir = os.path.abspath(relative_dir)
    os.makedirs(abs_dir, exist_ok=True)

    filename = f"{user_id}_{char_id_str}.png"
    full_save_path = os.path.join(abs_dir, filename)
    db_path = os.path.join(relative_dir, filename)

    file_info = await message.bot.get_file(file.file_id)
    image_bytes = BytesIO()
    await message.bot.download_file(file_info.file_path, image_bytes)
    image_bytes.seek(0)

    try:
        img = Image.open(image_bytes).convert("RGBA")

        img.thumbnail((400, 400), Image.Resampling.LANCZOS)

        img.save(full_save_path, "PNG", optimize=True)

        await users_col.update_one(
            {"user_id": str(user_id)},
            {"$set": {f"card_settings.stickers.{char_id_str}": db_path}},
            upsert=True
        )

        prompt_message_id = data.get("prompt_message_id")
        if prompt_message_id:
            try:
                await message.bot.delete_message(chat_id=message.chat.id, message_id=prompt_message_id)
            except Exception:
                pass

        await state.clear()
        await message.answer("✅ Your custom sticker has been saved and optimized!")

        char_name = CHARACTER_MAP.get(char_id_str, {}).get("name", f"ID: {char_id_str}")
        username = f"@{message.from_user.username}" if message.from_user.username else "No Username"

        admin_msg = (
            "⚠️ <b>New Sticker Alert</b>\n\n"
            f"👤 <b>User:</b> <code>{user_id}</code> ({username})\n"
            f"🎭 <b>Character:</b> {char_name}\n"
            f"🆔 <b>Char ID:</b> <code>{char_id_str}</code>\n"
            f"📁 <b>Path:</b> <code>{db_path}</code>\n\n"
            f"<i>Use /nuke_sticker {user_id} {char_id_str} to remove if inappropriate.</i>"
        )

        await message.bot.send_photo(
            chat_id=ADMIN_ID,
            photo=types.FSInputFile(full_save_path),
            caption=admin_msg,
            parse_mode="HTML"
        )

    except Exception as e:
        print(f"Sticker Process Error: {e}")
        await message.answer(f"❌ An error occurred while processing the image: {e}")

router3.message(CardSettings.waiting_for_splash)
async def handle_splash_upload(message: types.Message, state: FSMContext):
    data = await state.get_data()
    char_id_str = str(data.get("selected_char_id"))
    user_id = message.from_user.id

    if message.photo:
        file = message.photo[-1]
    elif message.document and message.document.mime_type.startswith("image/"):
        file = message.document
    else:
        return await message.answer("❌ Please send a valid Photo or Image Document.")

    if file.file_size > 2 * 1024 * 1024:  # 2MB limit for splash
        return await message.answer("❌ File too large! Please keep it under 2MB.")

    relative_dir = "custom_assets/splash_arts"
    abs_dir = os.path.abspath(relative_dir)
    os.makedirs(abs_dir, exist_ok=True)

    filename = f"{user_id}_{char_id_str}.png"
    full_save_path = os.path.join(abs_dir, filename)
    db_path = os.path.join(relative_dir, filename)

    file_info = await message.bot.get_file(file.file_id)
    image_bytes = BytesIO()
    await message.bot.download_file(file_info.file_path, image_bytes)
    image_bytes.seek(0)

    try:
        img = Image.open(image_bytes).convert("RGBA")

        # Resize to fit splash area, but keep aspect ratio
        img.thumbnail((1200, 890), Image.Resampling.LANCZOS)

        img.save(full_save_path, "PNG", optimize=True)

        await users_col.update_one(
            {"user_id": str(user_id)},
            {"$set": {f"card_settings.splash_arts.{char_id_str}": db_path}},
            upsert=True
        )

        prompt_message_id = data.get("prompt_message_id")
        if prompt_message_id:
            try:
                await message.bot.delete_message(chat_id=message.chat.id, message_id=prompt_message_id)
            except Exception:
                pass

        await state.clear()
        await message.answer("✅ Your custom splash art has been saved and optimized!")

        char_name = CHARACTER_MAP.get(char_id_str, {}).get("name", f"ID: {char_id_str}")
        username = f"@{message.from_user.username}" if message.from_user.username else "No Username"

        admin_msg = (
            "🌅 <b>New Splash Art Alert</b>\n\n"
            f"👤 <b>User:</b> <code>{user_id}</code> ({username})\n"
            f"🎭 <b>Character:</b> {char_name}\n"
            f"🆔 <b>Char ID:</b> <code>{char_id_str}</code>\n"
            f"📁 <b>Path:</b> <code>{db_path}</code>\n\n"
            f"<i>Use /nuke_splash {user_id} {char_id_str} to remove if inappropriate.</i>"
        )

        await message.bot.send_photo(
            chat_id=ADMIN_ID,
            photo=types.FSInputFile(full_save_path),
            caption=admin_msg,
            parse_mode="HTML"
        )

    except Exception as e:
        print(f"Splash Process Error: {e}")
        await message.answer(f"❌ An error occurred while processing the image: {e}")

router3.callback_query(F.data.startswith("reset_splash_"))
async def reset_splash_art(callback: types.CallbackQuery):
    char_id = callback.data.split("_")[2]
    user_id = callback.from_user.id

    filename = f"{user_id}_{char_id}.png"
    splash_path = os.path.join("custom_assets/splash_arts", filename)
    abs_path = os.path.abspath(splash_path)

    if os.path.exists(abs_path):
        os.remove(abs_path)

    await users_col.update_one(
        {"user_id": str(user_id)},
        {"$unset": {f"card_settings.splash_arts.{char_id}": ""}}
    )

    await callback.answer("✅ Custom splash art reset to default.")
    callback.data = f"pick_char_splash_{char_id}"
    await process_character_pick_splash(callback, None)

router3.message(Command("ban_sticker"), F.from_user.id == ADMIN_ID)
async def ban_sticker_command(message: types.Message):
    args = message.text.split()

    if len(args) < 3:
        return await message.answer(
            "⚠️ <b>Usage:</b>\n<code>/ban_sticker [user_id] [char_id]</code>",
            parse_mode="HTML"
        )

    target_user_id = args[1]
    target_char_id = args[2]

    filename = f"{target_user_id}_{target_char_id}.png"
    sticker_path = os.path.join("custom_assets/stickers", filename)
    abs_path = os.path.abspath(sticker_path)

    status_report = [f"🛡 <b>Moderation Report for {target_user_id}</b>"]

    try:
        if os.path.exists(abs_path):
            os.remove(abs_path)
            status_report.append("✅ File deleted from VPS storage.")
        else:
            status_report.append("❓ File not found on disk (already gone?).")
    except Exception as e:
        status_report.append(f"❌ Error deleting file: {e}")

    try:
        result = await users_col.update_one(
            {"user_id": str(target_user_id)},
            {"$unset": {f"card_settings.stickers.{target_char_id}": ""}}
        )

        if result.modified_count > 0:
            status_report.append("✅ Removed from Database.")
        else:
            status_report.append("❌ Not found in Database (check IDs).")

    except Exception as e:
        status_report.append(f"❌ MongoDB Error: {e}")

    await message.answer("\n".join(status_report), parse_mode="HTML")

router3.message(Command("ban_splash"), F.from_user.id == ADMIN_ID)
async def ban_splash_command(message: types.Message):
    args = message.text.split()

    if len(args) < 3:
        return await message.answer(
            "⚠️ <b>Usage:</b>\n<code>/ban_splash [user_id] [char_id]</code>",
            parse_mode="HTML"
        )

    target_user_id = args[1]
    target_char_id = args[2]

    filename = f"{target_user_id}_{target_char_id}.png"
    splash_path = os.path.join("custom_assets/splash_arts", filename)
    abs_path = os.path.abspath(splash_path)

    status_report = [f"🌅 <b>Moderation Report for {target_user_id}</b>"]

    try:
        if os.path.exists(abs_path):
            os.remove(abs_path)
            status_report.append("✅ File deleted from VPS storage.")
        else:
            status_report.append("❓ File not found on disk (already gone?).")
    except Exception as e:
        status_report.append(f"❌ Error deleting file: {e}")

    try:
        result = await users_col.update_one(
            {"user_id": str(target_user_id)},
            {"$unset": {f"card_settings.splash_arts.{target_char_id}": ""}}
        )

        if result.modified_count > 0:
            status_report.append("✅ Removed from Database.")
        else:
            status_report.append("❌ Not found in Database (check IDs).")

    except Exception as e:
        status_report.append(f"❌ MongoDB Error: {e}")

    await message.answer("\n".join(status_report), parse_mode="HTML")
