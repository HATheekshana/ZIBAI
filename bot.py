import asyncio
from handlers.settings import router3
from handlers.login import router4
from aiogram import Bot, Dispatcher
from config import BOT_TOKEN
from handlers import router_bc
from handlers.wish import router
from handlers.characters import router2
from services.daily import check_individual_dailies
from handlers.info import router5
from handlers.comparechar import router6
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from pytz import timezone
from handlers.teams import router_team


bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
dp.include_router(router)
dp.include_router(router2)
dp.include_router(router3)
dp.include_router(router4)
dp.include_router(router5)
dp.include_router(router6)
dp.include_router(router_team)
dp.include_router(router_bc)

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