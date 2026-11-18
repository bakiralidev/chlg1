import asyncio
import logging
import sys
from pathlib import Path

# Allow running directly from repo root (`python -m bot.main`) by adding /backend to sys.path
_BACKEND_DIR = str(Path(__file__).resolve().parents[1] / "backend")
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from app.core.config import settings
from bot.handlers import admin, menu, registration
from bot.middlewares import FloodControlMiddleware, PrivateChatOnlyMiddleware
from bot.scheduler import setup_scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("pychallenge.bot")
# Prevent httpx/aiogram from logging full bot token URLs at INFO level
logging.getLogger("aiogram.event").setLevel(logging.WARNING)


async def main() -> None:
    if not settings.TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN .env faylida o'rnatilmagan!")
        sys.exit(1)

    bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())

    # Global middlewares: private chats only + flood control
    dp.message.outer_middleware(PrivateChatOnlyMiddleware())
    dp.callback_query.outer_middleware(PrivateChatOnlyMiddleware())
    dp.message.middleware(FloodControlMiddleware(min_interval_secs=0.6))
    dp.callback_query.middleware(FloodControlMiddleware(min_interval_secs=0.5))

    # Routers (admin before menu so admin replies/commands take precedence)
    dp.include_router(admin.router)
    dp.include_router(registration.router)
    dp.include_router(menu.router)

    scheduler = setup_scheduler(bot)
    scheduler.start()
    logger.info("PyChallenge Telegram bot ishga tushdi (timezone=%s)", settings.TIMEZONE)

    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        scheduler.shutdown(wait=False)
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
