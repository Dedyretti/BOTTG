from aiogram import Router

from bot.filters.role import IsVerifiedUser

from .menu import router as menu_router
from .request import router as request_router
from .start import router as start_router
from .user_requests import router as user_requests_router

user_router = Router(name="user")
user_router.message.filter(IsVerifiedUser())
user_router.callback_query.filter(IsVerifiedUser())

user_router.include_router(start_router)
user_router.include_router(request_router)
user_router.include_router(user_requests_router)
user_router.include_router(menu_router)
