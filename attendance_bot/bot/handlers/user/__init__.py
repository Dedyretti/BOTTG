from aiogram import Router

from .menu import router as menu_router
from .request import router as requests_router

router = Router()
router.include_router(menu_router)
router.include_router(requests_router)
