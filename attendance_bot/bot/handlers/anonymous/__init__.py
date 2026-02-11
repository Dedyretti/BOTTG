from aiogram import Router

from .start import router as start_router
from .register import router as register_router

anonymous_router = Router(name="anonymous")

anonymous_router.include_router(start_router)
anonymous_router.include_router(register_router)
