# bot.py
import asyncio
from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties

from handlers import router
from database import create_tables
from config import TOKEN, DEFAULT_PARSE_MODE

async def main():
    create_tables()
    bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=DEFAULT_PARSE_MODE))
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)

    await bot.set_my_commands([
        BotCommand(command="start", description="Botni ishga tushirish")
    ])

    print("🚀 Bot ishga tushmoqda...")
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())