"""Middleware для работы с сессией базы данных."""

from aiogram import BaseMiddleware


class DbSessionMiddleware(BaseMiddleware):
    """Middleware для внедрения сессии БД в обработчики."""

    def __init__(self, sessionmaker):
        """Инициализирует middleware с фабрикой сессий."""
        self.sessionmaker = sessionmaker

    async def __call__(self, handler, event, data):
        """Создаёт сессию БД и передаёт её в обработчик."""
        async with self.sessionmaker() as session:
            data["session"] = session
            return await handler(event, data)
