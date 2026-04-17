import asyncio

from aiogram import Bot, Dispatcher
from config import BOT_TOKEN
from handlers.wish import router

from services.daily import check_individual_dailies

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from pytz import timezone


bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
dp.include_router(router)


async def main():
    print("Bot is live on EC2...")

    # ✅ Setup scheduler BEFORE polling
    lk_timezone = timezone("Asia/Colombo")
    scheduler = AsyncIOScheduler(timezone=lk_timezone)

    scheduler.add_job(
        check_individual_dailies,
        "interval",
        minutes=15,
        args=[bot]
    )

    scheduler.start()

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())