import asyncio
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties

from config import config
from core.logger import setup_logging

from database.session import AsyncSessionLocal as async_session
from middlewares.db import DbSessionMiddleware

from bot.handlers import router as main_router

logger = setup_logging(__name__)


async def main():

    bot = Bot(
        token=config.bot.token,
        default=DefaultBotProperties(parse_mode="HTML")
    )
    dp = Dispatcher(storage=MemoryStorage())

    dp.update.middleware(DbSessionMiddleware(async_session))
    dp.include_router(main_router)

    logger.info("Запуск бота")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
