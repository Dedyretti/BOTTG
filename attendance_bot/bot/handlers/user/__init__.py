from aiogram import Router

from bot.filters.role import IsVerifiedUser

from . import (
    my_requests,
    request_base,
    request_full,
    request_navigation,
    request_partial,
    start,
)

user_router = Router(name="user")

user_router.message.filter(IsVerifiedUser())
user_router.callback_query.filter(IsVerifiedUser())

user_router.include_router(start.router)
user_router.include_router(my_requests.router)
user_router.include_router(request_base.router)
user_router.include_router(request_full.router)
user_router.include_router(request_partial.router)
user_router.include_router(request_navigation.router)
