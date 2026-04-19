import json
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import BufferedInputFile 
from database.mongo import users_col
from services.get_enkadata import get_enkadata
from services.team_card import team_card   # IMPORTANT

router_team = Router()

# =========================
# LOAD CHAR DATA
# =========================
with open("assets/json/char.json", "r", encoding="utf-8") as f:
    CHARACTER_MAP = json.load(f)


# =========================
# FSM
# =========================
class TeamBuilder(StatesGroup):
    selecting = State()


# =========================
# GET SHOWCASE
# =========================
async def get_showcase(user_id: str):
    user = await users_col.find_one({"user_id": user_id})

    if not user or "genshin_uid" not in user:
        return None, "❌ Please /login <uid> first."

    uid = str(user["genshin_uid"]).strip()

    try:
        data = await get_enkadata(uid)
        showcase = data.get("showAvatarInfoList", [])
    except Exception as e:
        return None, f"❌ Enka error: {e}"

    if not showcase:
        return None, "❌ No characters in showcase."

    return showcase, None


# =========================
# ENSURE USER TEAM ARRAY
# =========================
async def ensure_user(user_id: str):
    user = await users_col.find_one({"user_id": user_id})

    if not user:
        await users_col.insert_one({"user_id": user_id, "teams": []})
        return {"user_id": user_id, "teams": []}

    if "teams" not in user:
        await users_col.update_one(
            {"user_id": user_id},
            {"$set": {"teams": []}}
        )
        user["teams"] = []

    return user


# =========================
# CHARACTER SELECT UI
# =========================
async def send_select(msg, showcase, selected):
    kb = InlineKeyboardBuilder()

    for c in showcase:
        cid = c["avatarId"]
        name = CHARACTER_MAP.get(str(cid), {}).get("name", str(cid))

        mark = "🟢" if cid in selected else "⚪"

        kb.button(text=f"{mark} {name}", callback_data=f"pick:{cid}")

    kb.button(text="✅ Done", callback_data="team_done")
    kb.button(text="❌ Remove", callback_data="team_remove")

    kb.adjust(2)

    text = f"Select up to 4 characters\nSelected: {len(selected)}/4"

    await msg.edit_text(text, reply_markup=kb.as_markup())


# =========================
# /TEAMS MENU
# =========================
@router_team.message(Command("teams"))
async def teams_menu(message: types.Message):
    user = await ensure_user(str(message.from_user.id))
    teams = user.get("teams", [])

    kb = InlineKeyboardBuilder()

    if teams:
        for i in range(len(teams)):
            kb.button(text=f"Team {i+1}", callback_data=f"view:{i}")

    kb.button(text="➕ Create Team", callback_data="add_team")
    kb.adjust(2)

    text = "Your Teams:" if teams else "No teams yet. Create one ➕"

    await message.reply(text, reply_markup=kb.as_markup())


# =========================
# CREATE TEAM
# =========================
@router_team.callback_query(F.data == "add_team")
async def add_team(callback: types.CallbackQuery, state: FSMContext):
    showcase, error = await get_showcase(str(callback.from_user.id))

    if error:
        return await callback.answer(error, show_alert=True)

    await state.set_state(TeamBuilder.selecting)
    await state.update_data(selected=[])

    await send_select(callback.message, showcase, [])


# =========================
# PICK CHAR
# =========================
@router_team.callback_query(F.data.startswith("pick:"))
async def pick(callback: types.CallbackQuery, state: FSMContext):
    cid = int(callback.data.split(":")[1])

    data = await state.get_data()
    selected = data.get("selected", [])

    if cid in selected:
        selected.remove(cid)
    else:
        if len(selected) >= 4:
            return await callback.answer("Max 4 characters!", show_alert=True)
        selected.append(cid)

    await state.update_data(selected=selected)

    showcase, _ = await get_showcase(str(callback.from_user.id))
    await send_select(callback.message, showcase, selected)


# =========================
# REMOVE LAST
# =========================
@router_team.callback_query(F.data == "team_remove")
async def remove(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    selected = data.get("selected", [])

    if selected:
        selected.pop()

    await state.update_data(selected=selected)

    showcase, _ = await get_showcase(str(callback.from_user.id))
    await send_select(callback.message, showcase, selected)


# =========================
# SAVE TEAM
# =========================
@router_team.callback_query(F.data == "team_done")
async def done(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    selected = data.get("selected", [])

    if not selected:
        return await callback.answer("Select at least 1 character", show_alert=True)

    await users_col.update_one(
        {"user_id": str(callback.from_user.id)},
        {"$push": {"teams": {"chars": selected}}}
    )

    await state.clear()
    await callback.message.edit_text("✅ Team saved!")


# =========================
# VIEW TEAM
# =========================
@router_team.callback_query(F.data.startswith("view:"))
async def view(callback: types.CallbackQuery):
    idx = int(callback.data.split(":")[1])

    user = await ensure_user(str(callback.from_user.id))
    teams = user.get("teams", [])

    if idx >= len(teams):
        return await callback.answer("Team not found", show_alert=True)

    team = teams[idx]

    char_names = [
        CHARACTER_MAP.get(str(cid), {}).get("name", str(cid))
        for cid in team["chars"]
    ]

    kb = InlineKeyboardBuilder()
    kb.button(text="📊 Show Team", callback_data=f"show:{idx}")
    kb.button(text="🗑 Delete", callback_data=f"delete:{idx}")
    kb.button(text="⬅ Back", callback_data="back")
    kb.adjust(1)

    await callback.message.edit_text(
        f"🏷 Team {idx+1}\n\n👥 Characters:\n" + "\n".join(char_names),
        reply_markup=kb.as_markup()
    )



# Ensure this is imported

@router_team.callback_query(F.data.startswith("show:"))
async def show_team(callback: types.CallbackQuery):
    idx = int(callback.data.split(":")[1])
    user = await users_col.find_one({"user_id": str(callback.from_user.id)})
    teams = user.get("teams", [])

    if idx >= len(teams):
        return await callback.answer("Not found", show_alert=True)

    team = teams[idx]
    uid = str(user["genshin_uid"])

    # This returns your BytesIO object
    img_buffer = await team_card(uid, team["chars"])

    if img_buffer:
        # WRAP IT HERE: This is what aiogram 3.x expects
        photo = BufferedInputFile(img_buffer.getvalue(), filename=f"team_{idx}.png")
        
        await callback.message.answer_photo(photo, caption=f"✨ Team {idx+1}")
        await callback.answer()
    else:
        await callback.answer("❌ Failed to generate team card", show_alert=True)

@router_team.callback_query(F.data.startswith("delete:"))
async def delete(callback: types.CallbackQuery):
    idx = int(callback.data.split(":")[1])

    await users_col.update_one(
        {"user_id": str(callback.from_user.id)},
        {"$unset": {f"teams.{idx}": 1}}
    )

    await users_col.update_one(
        {"user_id": str(callback.from_user.id)},
        {"$pull": {"teams": None}}
    )

    await callback.message.edit_text("❌ Team deleted")


# =========================
# BACK
# =========================
@router_team.callback_query(F.data == "back")
async def back(callback: types.CallbackQuery):
    await teams_menu(callback.message)