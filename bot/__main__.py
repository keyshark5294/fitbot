"""Entrypoint. Запуск: python -m bot"""
import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from bot.config import settings
from bot.handlers import router as main_router
from bot.middlewares.db import DbSessionMiddleware
from bot.services.scheduler import reminder_ticker
from bot.utils.logging import setup_logging


async def main() -> None:
    setup_logging()
    log = logging.getLogger("bot")

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    if settings.redis_url:
        from aiogram.fsm.storage.redis import RedisStorage

        storage = RedisStorage.from_url(settings.redis_url)
    else:
        storage = MemoryStorage()

    dp = Dispatcher(storage=storage)
    dp.update.outer_middleware(DbSessionMiddleware())
    dp.include_router(main_router)

    ticker_task = asyncio.create_task(reminder_ticker(bot))

    await bot.delete_webhook(drop_pending_updates=True)
    try:
        log.info("Start polling")
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        ticker_task.cancel()
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass
