import asyncio
import io
import logging
from datetime import datetime, timedelta

from aiogram import Bot
from aiogram.types import BufferedInputFile

from database.mongo import users_col
from services.image_service import combine_images
from config import CURRENT_RATE_UP_KEY, CURRENT_RATE_UP_NAME


async def check_individual_dailies(bot: Bot):
    now = datetime.utcnow()
    threshold = now - timedelta(days=1)

    # ✅ Only target valid users
    cursor = users_col.find({
        "$or": [
            {"last_daily_wish": {"$lte": threshold}},
            {"last_daily_wish": {"$exists": False}}
        ],
        "notification_sent": {"$ne": True},
        "started": True,              # ✅ user has started bot
        "blocked": {"$ne": True}      # ✅ user didn't block bot
    })

    # ✅ Generate image ONCE
    file_path = f"https://raw.githubusercontent.com/Mantan21/Genshin-Impact-Wish-Simulator/master/src/images/characters/splash-art/5star/{CURRENT_RATE_UP_KEY}.webp"
    bg_path = "https://raw.githubusercontent.com/Mantan21/Genshin-Impact-Wish-Simulator/master/src/images/background/splash-background.webp"

    combined_img = await combine_images(file_path, bg_path, CURRENT_RATE_UP_NAME, 5)

    img_byte_arr = io.BytesIO()
    combined_img.save(img_byte_arr, format="PNG")
    img_data = img_byte_arr.getvalue()

    async for user in cursor:
        user_id = user.get("user_id")

        try:
            # ✅ Skip invalid IDs
            if not user_id:
                continue

            user_id = int(user_id)

            # ✅ Skip bot accounts
            try:
                chat = await bot.get_chat(user_id)
                if chat.type != "private":
                    continue
            except Exception:
                continue

            photo_file = BufferedInputFile(img_data, filename="wish.png")

            await bot.send_photo(
                chat_id=user_id,
                photo=photo_file,
                caption=(
                    "✨ *Your Daily Wish is ready!* ✨\n"
                    "Claim it now to keep your streak alive!\n"
                    f"Current Rate up: {CURRENT_RATE_UP_NAME}"
                ),
                parse_mode="Markdown"
            )

            # ✅ Mark as sent
            await users_col.update_one(
                {"user_id": str(user_id)},
                {"$set": {"notification_sent": True}}
            )

            await asyncio.sleep(0.05)  # ✅ small delay (rate limit safety)

        except Exception as e:
            err = str(e)

            # 🔴 Handle known Telegram errors smartly
            if "bot was blocked" in err:
                await users_col.update_one(
                    {"user_id": str(user_id)},
                    {"$set": {"blocked": True}}
                )

            elif "can't initiate conversation" in err:
                await users_col.update_one(
                    {"user_id": str(user_id)},
                    {"$set": {"started": False}}
                )

            elif "bots can't send messages to bots" in err:
                await users_col.update_one(
                    {"user_id": str(user_id)},
                    {"$set": {"is_bot": True}}
                )

            logging.error(f"Failed to notify {user_id}: {err}")