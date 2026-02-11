from aiogram import Router

from bot.filters.role import IsAdmin
from .menu import router as menu_router
from .start import router as start_router
from .request import router as request_router
from .employees import router as employees_router
from .invite_codes import router as invite_codes_router


admin_router = Router(name="admin")
admin_router.message.filter(IsAdmin())
admin_router.callback_query.filter(IsAdmin())

admin_router.include_router(menu_router)
admin_router.include_router(start_router)
admin_router.include_router(request_router)
admin_router.include_router(employees_router)
admin_router.include_router(invite_codes_router)
