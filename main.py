import asyncio
import os
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

from handlers.commands import router as commands_router, db
from handlers.admin import router as admin_router
from middlewares.logger import ActionLoggerMiddleware
from middlewares.antispam import AntiSpamMiddleware
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise ValueError("Бот токен не знайдено! Додай його у файл .env")

bot = Bot(
    token=TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML),
)

dp = Dispatcher()
# реєструємо антиспам глобально в самому ядрі
dp.message.middleware(AntiSpamMiddleware(limit=0.5))

dp.include_router(admin_router)
dp.include_router(commands_router)


async def main():
    print("Initializing Database...")
    await db.init_db()
    
    print("Setting up Middlewares...")
    dp.message.middleware(ActionLoggerMiddleware(db))
    dp.callback_query.middleware(ActionLoggerMiddleware(db))

    print("Bot started...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())