import os
import asyncio
from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
# --- WEBHOOK UCHUN QO'SHILGANLAR ---
from aiohttp import web
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
# -----------------------------------

from handlers import router
from database import create_tables
from config import TOKEN, DEFAULT_PARSE_MODE

# --- RENDER.COM UCHUN WEBHOOK SOZLAMALARI ---
# Render portini avtomatik olish
WEB_SERVER_HOST = "0.0.0.0"
WEB_SERVER_PORT = int(os.environ.get("PORT", 8000))

# Render.com avtomatik beradigan tashqi URLni olish.
# Eslatma: BOT_TOKEN Render ENV'da o'rnatilgan bo'lishi shart!
BOT_TOKEN = os.environ.get("BOT_TOKEN", TOKEN) # Agar ENV bo'lmasa, config'dan oladi
BASE_WEBHOOK_URL = os.environ.get("RENDER_EXTERNAL_URL") 

# Webhook manzili (xavfsizlik uchun Token ishlatiladi)
WEBHOOK_PATH = f"/webhook/{BOT_TOKEN}" 
WEBHOOK_URL = f"{BASE_WEBHOOK_URL}{WEBHOOK_PATH}" 
# --------------------------------------------

async def on_startup(bot: Bot) -> None:
    """Bot ishga tushganda Webhook manzilini Telegram'ga o'rnatadi."""
    if BASE_WEBHOOK_URL:
        # Webhook URL'ini Telegram'ga o'rnatish
        await bot.set_webhook(WEBHOOK_URL, drop_pending_updates=True)
        print(f"✅ Webhook manzil muvaffaqiyatli o'rnatildi: {WEBHOOK_URL}")
    else:
        print("⚠️ RENDER_EXTERNAL_URL topilmadi. Webhook o'rnatilmadi.")


async def main() -> None:
    create_tables()
    
    # TOKEN ni env-variable dan olishni birinchi o'ringa qo'yamiz
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=DEFAULT_PARSE_MODE))
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)
    
    # /start buyrug'ini o'rnatish
    await bot.set_my_commands([
        BotCommand(command="start", description="Botni ishga tushirish")
    ])

    print("🚀 Bot ishga tushmoqda...")
    
    if BASE_WEBHOOK_URL:
        # --- WEBHOOK ISHGA TUSHIRISH MANTIG'I ---
        dp.startup.register(on_startup)

        # Aiohttp ilovasini va Webhook handler'ni sozlash
        app = web.Application()
        webhook_requests_handler = SimpleRequestHandler(
            dispatcher=dp,
            bot=bot,
        )
        # Telegramdan keladigan POST so'rovlarini ushlab oluvchi yo'lni o'rnatish
        webhook_requests_handler.register(app, path=WEBHOOK_PATH)
        
        # Veb-serverni ishga tushirish (Render.com talab qilganidek Portni tinglash!)
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, host=WEB_SERVER_HOST, port=WEB_SERVER_PORT)
        await site.start()
        
        print(f"🤖 Veb-server {WEB_SERVER_HOST}:{WEB_SERVER_PORT} portida tinglamoqda.")
        await asyncio.Event().wait() # Serverni doimiy ushlab turish
        
    else:
        # --- LONG POLLING ISHLATISH MANTIG'I (Favqulodda holatda) ---
        print("Webhook o'rnatilmagan, Long Polling rejimida ishga tushirilmoqda...")
        try:
            await dp.start_polling(bot)
        finally:
            await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())