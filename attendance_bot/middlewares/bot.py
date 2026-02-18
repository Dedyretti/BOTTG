# from typing import Any, Awaitable, Callable

# from aiogram import BaseMiddleware, Bot
# from aiogram.types import TelegramObject


# class BotMiddleware(BaseMiddleware):
#     """Middleware для передачи bot в хендлеры."""

#     def __init__(self, bot: Bot):
#         """Инициализация middleware."""

#         super().__init__()
#         self.bot = bot

#     async def __call__(
#         self,
#         handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
#         event: TelegramObject,
#         data: dict[str, Any]
#     ) -> Any:
#         """Добавляет bot в данные хендлера."""

#         data["bot"] = self.bot
#         return await handler(event, data)
