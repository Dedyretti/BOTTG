"""Главный роутер обработчиков."""

from aiogram import Router

from .start import router as start_router
from .admin import router as admin_router
from .user import router as user_router

router = Router()
router.include_router(start_router)
router.include_router(admin_router)
router.include_router(user_router)
