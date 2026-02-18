import asyncio
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties

from config import config
from core.logger import setup_logging

from database.session import AsyncSessionLocal as async_session
from middlewares.db import DbSessionMiddleware
# from middlewares.bot import BotMiddleware

from bot.handlers import admin_router, user_router, anonymous_router

logger = setup_logging(__name__)


async def on_startup(bot: Bot) -> None:
    """Действия при запуске бота."""

    logger.info("Бот запущен")


async def on_shutdown(bot: Bot) -> None:
    """Действия при остановке бота."""

    logger.info("Бот остановлен")


async def main():

    bot = Bot(
        token=config.bot.token,
        default=DefaultBotProperties(parse_mode="HTML")
    )
    dp = Dispatcher(storage=MemoryStorage())

    dp.update.middleware(DbSessionMiddleware(async_session))
    # dp.update.middleware(BotMiddleware(bot))

    dp.include_router(admin_router)
    dp.include_router(user_router)
    dp.include_router(anonymous_router)

    logger.info("Запуск бота")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    try:
        await dp.start_polling(bot)
    except asyncio.CancelledError:
        logger.info("Получен сигнал остановки")
    finally:
        await bot.session.close()
        logger.info("Сессия бота закрыта")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен пользователем (Ctrl+C)")
    except SystemExit:
        logger.info("Бот завершил работу")
