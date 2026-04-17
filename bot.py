import asyncio
from aiogram import Bot, Dispatcher
from config import BOT_TOKEN
from handlers.wish import router

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
dp.include_router(router)

async def main():
    print("Bot is live on EC2...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())