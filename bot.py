import asyncio
from aiogram import Bot, Dispatcher
from config import BOT_TOKEN
from handlers import wish

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Register routers
dp.include_router(wish.router)

async def main():
    print("Bot started...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())