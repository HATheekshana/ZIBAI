
from aiogram import Router, types
from aiogram.filters import Command
import aiohttp
from database.mongo import users_col

router4 = Router()
router4.message(Command("login"))
async def fetch_enka_data(uid: str):
    url = f"https://enka.network/api/uid/{uid}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as response:
            if response.status == 200:
                return await response.json()
            return None
router4.message(Command("login"))
async def login_uid(message: types.Message):
    args = message.text.split()
    if len(args) < 2:
        return await message.answer("❓ <b>Usage:</b> `/login <uid>`",parse_mode="HTML")

    uid = args[1]
    if not uid.isdigit():
        return await message.answer("❌ Please enter a numeric UID.")

    status_msg = await message.answer(f"🔍 Verifying UID {uid}...")
    data = await fetch_enka_data(uid)

    if not data or "playerInfo" not in data:
        return await status_msg.edit_text("❌ UID not found or Showcase is private.")

    player = data["playerInfo"]
    await users_col.update_one(
        {"user_id": str(message.from_user.id)},
        {"$set": {"genshin_uid": int(uid)}},
        upsert=True
    )
    await status_msg.edit_text(f"✅ <b>Login Successful! <code>{uid}</code></b>\n👤 <b>Player:</b> {player.get('name')} (AR {player.get('level')})", parse_mode="HTML")
router4.message(Command("logout"))
async def logout_uid(message: types.Message):
    user_id = str(message.from_user.id)
    user_data = await users_col.find_one({"user_id": user_id})

    if not user_data or "genshin_uid" not in user_data:
        return await message.answer("ℹ️ You are not logged in yet.")

    await users_col.update_one(
        {"user_id": user_id},
        {"$unset": {"genshin_uid": ""}}
    )

    await message.answer("✅ <b>Logout Successful!</b>\nYour UID has been unlinked from this account.", parse_mode="HTML")