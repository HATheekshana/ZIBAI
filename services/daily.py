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

    cursor = users_col.find({
        "$or": [
            {"last_daily_wish": {"$lte": threshold}},
            {"last_daily_wish": {"$exists": False}}
        ],
        "notification_sent": {"$ne": True}
    })

    # ✅ Generate image ONCE
    file_path = f"https://raw.githubusercontent.com/Mantan21/Genshin-Impact-Wish-Simulator/master/src/images/characters/splash-art/5star/{CURRENT_RATE_UP_KEY}.webp"
    bg_path = "https://raw.githubusercontent.com/Mantan21/Genshin-Impact-Wish-Simulator/master/src/images/background/splash-background.webp"

    combined_img = await combine_images(file_path, bg_path, CURRENT_RATE_UP_NAME, 5)

    img_byte_arr = io.BytesIO()
    combined_img.save(img_byte_arr, format="PNG")
    img_data = img_byte_arr.getvalue()

    async for user in cursor:
        try:
            photo_file = BufferedInputFile(img_data, filename="wish.png")

            await bot.send_photo(
                chat_id=int(user["user_id"]),  # ✅ ensure int
                photo=photo_file,
                caption=(
                    "✨ *Your Daily Wish is ready!* ✨\n"
                    "Claim it now to keep your streak alive!\n"
                    f"Current Rate up: {CURRENT_RATE_UP_NAME}"
                ),
                parse_mode="Markdown"
            )

            await users_col.update_one(
                {"user_id": user["user_id"]},
                {"$set": {"notification_sent": True}}
            )

            await asyncio.sleep(0.1)  # ✅ slightly safer

        except Exception as e:
            logging.error(f"Failed to notify {user['user_id']}: {e}")