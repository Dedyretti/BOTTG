from aiogram import Router

from bot.filters import IsVerifiedUser
from .menu import router as menu_router
from .start import router as start_router
from .request import router as requests_router

user_router = Router(name="user")
user_router.message.filter(IsVerifiedUser())
user_router.callback_query.filter(IsVerifiedUser())

user_router.include_router(menu_router)
user_router.include_router(start_router)
user_router.include_router(requests_router)
