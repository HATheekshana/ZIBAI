import os
from aiogram import Router, types,F,Bot
import asyncio
import logging
from aiogram.filters import Command
from database.mongo import users_col ,groups_col
from dotenv import load_dotenv

load_dotenv()
ADMIN_VAL = os.getenv("ADMIN_ID")

ADMIN_ID = int(ADMIN_VAL)
router_bc = Router()
@router_bc.message(Command("broadcastg"))
async def broadcast_groups_smart(message: types.Message, bot: Bot):
    if message.from_user.id != ADMIN_ID:
        await message.answer("🚫 **Access Denied**")
        return

    photo_id = None
    broadcast_text = ""

    if message.photo:
        photo_id = message.photo[-1].file_id
        raw_caption = message.caption or ""
        if raw_caption.startswith("/broadcastg"):
            parts = raw_caption.split(maxsplit=1)
            broadcast_text = parts[1] if len(parts) > 1 else ""
        else:
            broadcast_text = raw_caption
    else:
        parts = message.text.split(maxsplit=1)
        if len(parts) > 1:
            broadcast_text = parts[1]

    if not broadcast_text and not photo_id:
        await message.answer(
            "❓ **Usage:**\n"
            "1. Send an image with caption: `/broadcastg [text]`\n"
            "2. Send text: `/broadcastg [text]`"
        )
        return

    status_msg = await message.answer("⏳ **Broadcasting to groups...**")

    cursor = groups_col.find({})
    success, fail = 0, 0

    async for group in cursor:
        try:
            target_id = group["chat_id"]

            if photo_id:
                await bot.send_photo(
                    chat_id=target_id,
                    photo=photo_id,
                    caption=broadcast_text,
                    parse_mode="HTML"
                )
            else:
                await bot.send_message(
                    chat_id=target_id,
                    text=broadcast_text,
                    parse_mode="HTML"
                )

            success += 1
            await asyncio.sleep(0.3)

        except Exception as e:
            logging.error(f"Group {group.get('chat_id')} broadcast error: {e}")
            fail += 1

    await status_msg.edit_text(
        f"✅ **Group Broadcast Complete**\n"
        f"⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯\n"
        f"👥 **Delivered:** {success}\n"
        f"🚫 **Failed/Blocked:** {fail}"
    )
@router_bc.message(Command("broadcast"))
async def broadcast_smart(message: types.Message, bot: Bot):
    if message.from_user.id != ADMIN_ID:
        await message.answer("🚫 **Access Denied**")
        return

    raw_content = message.caption if message.photo else message.text

    parts = raw_content.split(maxsplit=1)
    broadcast_text = parts[1] if len(parts) > 1 else ""

    photo_id = message.photo[-1].file_id if message.photo else None

    if not broadcast_text and not photo_id:
        await message.answer("❓ **Usage:**\n1. Send an image with caption `/broadcast [text]`\n2. Send just `/broadcast [text]`")
        return

    status_msg = await message.answer("⏳ **Broadcasting to all travelers...**")

    cursor = users_col.find({})
    success, fail = 0, 0

    async for user in cursor:
        try:
            target_id = user["user_id"]
            if photo_id:
                await bot.send_photo(
                    chat_id=target_id,
                    photo=photo_id,
                    caption=broadcast_text,
                    parse_mode="HTML"
                )
            else:
                await bot.send_message(
                    chat_id=target_id,
                    text=broadcast_text,
                    parse_mode="HTML"
                )

            success += 1
            await asyncio.sleep(0.05)

        except Exception as e:
            logging.error(f"Failed to send to {user.get('user_id')}: {e}")
            fail += 1

    await status_msg.edit_text(
        f"✅ **Broadcast Complete**\n"
        f"⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯\n"
        f"🟢 **Success:** {success}\n"
        f"🔴 **Failed:** {fail}"
    )