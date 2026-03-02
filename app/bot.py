import asyncio
from aiogram import Bot, Dispatcher

from .config import BOT_TOKEN
from .db import init_db, create_tables
from .handlers import (
    start, topics, review, profile, reminders,
    subjects, materials, help_friend, assistant, gallery
)
from . import scheduler


async def main():
    print("Запуск SmartStudy...")

    if not BOT_TOKEN:
        print("❌ BOT_TOKEN не найден. Проверь .env")
        return

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()

    await init_db()
    await create_tables()

    # на всякий случай чистим вебхук и старые апдейты (очень полезно)
    await bot.delete_webhook(drop_pending_updates=True)

    dp.include_router(start.router)
    dp.include_router(topics.router)
    dp.include_router(review.router)
    dp.include_router(profile.router)
    dp.include_router(reminders.router)
    dp.include_router(subjects.router)
    dp.include_router(help_friend.router)
    dp.include_router(assistant.router)
    dp.include_router(materials.router)
    dp.include_router(gallery.router)

    # запускаем планировщик (НЕ ДОЛЖЕН запускать polling внутри)
    asyncio.create_task(scheduler.start(bot))

    print("База подключена")
    print("Бот запущен")
    await dp.start_polling(bot)