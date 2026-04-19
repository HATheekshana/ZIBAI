from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

from database.mongo import users_col
from services.get_genshindata import get_enkadata

router_team = Router()

# =========================
# FSM
# =========================
class TeamBuilder(StatesGroup):
    selecting = State()


# =========================
# ✅ Ensure user exists
# =========================
async def ensure_user(user_id: int):
    user = await users_col.find_one({"user_id": user_id})

    if not user:
        await users_col.insert_one({
            "user_id": user_id,
            "teams": []
        })
        return {"user_id": user_id, "teams": []}

    # If user exists but no teams field
    if "teams" not in user:
        await users_col.update_one(
            {"user_id": user_id},
            {"$set": {"teams": []}}
        )
        user["teams"] = []

    return user


# =========================
# Helpers
# =========================
async def get_showcase_chars(uid):
    data = await get_enkadata(uid)
    return [c["avatarId"] for c in data.get("avatarInfoList", [])]


async def send_char_select(message: types.Message, chars, selected):
    kb = InlineKeyboardBuilder()

    for cid in chars:
        mark = "🟢" if cid in selected else "⚪"
        kb.button(text=f"{mark} {cid}", callback_data=f"pick:{cid}")

    kb.button(text="✅ Done", callback_data="team_done")
    kb.button(text="❌ Remove Last", callback_data="team_remove")

    kb.adjust(3)

    text = "Select up to 4 characters:\n"
    text += f"\nSelected: {selected}"

    await message.edit_text(text, reply_markup=kb.as_markup())


# =========================
# /teams command
# =========================
@router_team.message(Command("teams"))
async def teams_menu(message: types.Message):
    user = await ensure_user(message.from_user.id)
    teams = user.get("teams", [])

    kb = InlineKeyboardBuilder()

    if teams:
        for i, t in enumerate(teams):
            kb.button(text=f"Team {i+1}", callback_data=f"team_view:{i}")

    kb.button(text="➕", callback_data="team_add")
    kb.adjust(2)

    if not teams:
        text = "You don't have any teams yet.\nClick ➕ to create one."
    else:
        text = "Your Teams:"

    await message.answer(text, reply_markup=kb.as_markup())


# =========================
# Add team
# =========================
@router_team.callback_query(F.data == "team_add")
async def team_add(callback: types.CallbackQuery, state: FSMContext):
    uid = callback.from_user.id

    chars = await get_showcase_chars(uid)

    if not chars:
        await callback.answer("No showcase characters found!", show_alert=True)
        return

    await state.set_state(TeamBuilder.selecting)
    await state.update_data(selected=[])

    await send_char_select(callback.message, chars, [])


# =========================
# Pick char
# =========================
@router_team.callback_query(F.data.startswith("pick:"))
async def pick_char(callback: types.CallbackQuery, state: FSMContext):
    cid = int(callback.data.split(":")[1])

    data = await state.get_data()
    selected = data.get("selected", [])

    if cid in selected:
        selected.remove(cid)
    else:
        if len(selected) >= 4:
            await callback.answer("Max 4 characters!", show_alert=True)
            return
        selected.append(cid)

    await state.update_data(selected=selected)

    chars = await get_showcase_chars(callback.from_user.id)
    await send_char_select(callback.message, chars, selected)


# =========================
# Remove last
# =========================
@router_team.callback_query(F.data == "team_remove")
async def remove_char(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    selected = data.get("selected", [])

    if selected:
        selected.pop()

    await state.update_data(selected=selected)

    chars = await get_showcase_chars(callback.from_user.id)
    await send_char_select(callback.message, chars, selected)


# =========================
# Save team
# =========================
@router_team.callback_query(F.data == "team_done")
async def team_done(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    selected = data.get("selected", [])

    if not selected:
        await callback.answer("Pick at least 1 character!", show_alert=True)
        return

    user_id = callback.from_user.id

    await users_col.update_one(
        {"user_id": user_id},
        {"$push": {"teams": {"name": "Team", "chars": selected}}},
        upsert=True
    )

    await state.clear()
    await callback.message.edit_text("✅ Team saved!")


# =========================
# View team
# =========================
@router_team.callback_query(F.data.startswith("team_view:"))
async def team_view(callback: types.CallbackQuery):
    user = await ensure_user(callback.from_user.id)

    index = int(callback.data.split(":")[1])
    teams = user.get("teams", [])

    if index >= len(teams):
        await callback.answer("Team not found", show_alert=True)
        return

    team = teams[index]

    kb = InlineKeyboardBuilder()
    kb.button(text="📊 Show Team", callback_data=f"team_show:{index}")
    kb.button(text="🗑 Remove", callback_data=f"team_delete:{index}")
    kb.button(text="⬅ Back", callback_data="teams_back")
    kb.adjust(1)

    await callback.message.edit_text(
        f"Team {index+1}\nChars: {team['chars']}",
        reply_markup=kb.as_markup()
    )


# =========================
# Delete team
# =========================
@router_team.callback_query(F.data.startswith("team_delete:"))
async def team_delete(callback: types.CallbackQuery):
    index = int(callback.data.split(":")[1])

    await users_col.update_one(
        {"user_id": callback.from_user.id},
        {"$unset": {f"teams.{index}": 1}}
    )

    await users_col.update_one(
        {"user_id": callback.from_user.id},
        {"$pull": {"teams": None}}
    )

    await callback.message.edit_text("❌ Team removed")


# =========================
# Back
# =========================
@router_team.callback_query(F.data == "teams_back")
async def teams_back(callback: types.CallbackQuery):
    user = await ensure_user(callback.from_user.id)
    teams = user.get("teams", [])

    kb = InlineKeyboardBuilder()

    for i, t in enumerate(teams):
        kb.button(text=f"Team {i+1}", callback_data=f"team_view:{i}")

    kb.button(text="➕", callback_data="team_add")
    kb.adjust(2)

    await callback.message.edit_text("Your Teams:", reply_markup=kb.as_markup())