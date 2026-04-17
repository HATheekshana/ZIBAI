import asyncio
from aiogram import Bot, Dispatcher
from config import BOT_TOKEN
from handlers import wish
from services.cache import get_cached_image, init_cache

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Register routers
dp.include_router(wish.router)

async def main():
    print("Bot started...")
    await get_cached_image() 
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())