import json
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

from database.mongo import users_col
from services.get_enkadata import get_enkadata

router_team = Router()

# Load character names
with open("assets/json/char.json", "r", encoding="utf-8") as f:
    CHARACTER_MAP = json.load(f)

class TeamBuilder(StatesGroup):
    selecting = State()

async def get_showcase_chars(user_id: str):
    user_data = await users_col.find_one({"user_id": user_id})
    if not user_data or "genshin_uid" not in user_data:
        return None, "❌ Please /login <uid> first."

    db_uid = str(user_data["genshin_uid"]).strip()
    try:
        user_info_enka = await get_enkadata(db_uid)
        showcase_items = user_info_enka.get("showAvatarInfoList", [])
    except Exception:
        return None, "❌ Failed to reach Enka.network."

    if not showcase_items:
        return None, "❌ No characters found! Enable 'Show Character Details' in-game."
    
    return showcase_items, None

async def send_char_select(message: types.Message, showcase, selected):
    kb = InlineKeyboardBuilder()
    for char in showcase:
        cid = char.get("avatarId")
        name = CHARACTER_MAP.get(str(cid), {}).get("name", str(cid))
        mark = "🟢" if cid in selected else "⚪"
        kb.button(text=f"{mark} {name}", callback_data=f"pick:{cid}")

    kb.button(text="✅ Done", callback_data="team_done")
    kb.button(text="❌ Remove", callback_data="team_remove")
    kb.adjust(2)
    
    text = f"Select characters (Max 4):\nSelected: {len(selected)}/4"
    await message.edit_text(text, reply_markup=kb.as_markup())

@router_team.message(Command("teams"))
async def teams_menu(message: types.Message):
    user = await users_col.find_one({"user_id": str(message.from_user.id)})
    if not user or "genshin_uid" not in user:
        return await message.answer("❌ You must /login <uid> before managing teams!")

    teams = user.get("teams", [])
    kb = InlineKeyboardBuilder()
    for i, t in enumerate(teams):
        kb.button(text=f"Team {i+1}", callback_data=f"team_view:{i}")
    kb.button(text="➕ Add New", callback_data="team_add")
    kb.adjust(2)
    await message.answer("Your Teams:", reply_markup=kb.as_markup())

@router_team.callback_query(F.data == "team_add")
async def team_add(callback: types.CallbackQuery, state: FSMContext):
    showcase, error = await get_showcase_chars(str(callback.from_user.id))
    if error: return await callback.answer(error, show_alert=True)
    
    await state.set_state(TeamBuilder.selecting)
    await state.update_data(selected=[])
    await send_char_select(callback.message, showcase, [])

@router_team.callback_query(F.data.startswith("pick:"))
async def pick_char(callback: types.CallbackQuery, state: FSMContext):
    cid = int(callback.data.split(":")[1])
    data = await state.get_data()
    selected = data.get("selected", [])

    if cid in selected:
        selected.remove(cid)
    elif len(selected) < 4:
        selected.append(cid)
    else:
        return await callback.answer("Max 4 characters!", show_alert=True)

    await state.update_data(selected=selected)
    showcase, _ = await get_showcase_chars(str(callback.from_user.id))
    await send_char_select(callback.message, showcase, selected)

@router_team.callback_query(F.data == "team_remove")
async def remove_char(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    selected = data.get("selected", [])
    if selected: selected.pop()
    await state.update_data(selected=selected)
    showcase, _ = await get_showcase_chars(str(callback.from_user.id))
    await send_char_select(callback.message, showcase, selected)

@router_team.callback_query(F.data == "team_done")
async def team_done(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    selected = data.get("selected", [])
    if not selected: return await callback.answer("Pick at least 1!", show_alert=True)

    await users_col.update_one(
        {"user_id": str(callback.from_user.id)},
        {"$push": {"teams": {"chars": selected}}}
    )
    await state.clear()
    await callback.message.edit_text("✅ Team saved!")
    
@router_team.callback_query(F.data.startswith("team_view:"))
async def team_view(callback: types.CallbackQuery):
    idx = int(callback.data.split(":")[1])
    user = await users_col.find_one({"user_id": str(callback.from_user.id)})
    team = user["teams"][idx]
    
    kb = InlineKeyboardBuilder()
    kb.button(text="📊 Show Team", callback_data=f"team_show:{idx}")
    kb.button(text="🗑 Remove", callback_data=f"team_delete:{idx}")
    kb.button(text="⬅ Back", callback_data="teams_back")
    kb.adjust(1)
    await callback.message.edit_text(f"Team {idx+1} Chars: {team['chars']}", reply_markup=kb.as_markup())

@router_team.callback_query(F.data == "teams_back")
async def teams_back(callback: types.CallbackQuery):
    # Re-trigger main menu
    await teams_menu(callback.message)