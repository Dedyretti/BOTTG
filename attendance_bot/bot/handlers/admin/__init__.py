from aiogram import Router

from .menu import router as menu_router
from .employees import router as employees_router
from .add_employees import router as add_employee_router
from .invite_codes import router as invite_codes_router
from .delete import router as delete_router

router = Router()
router.include_router(menu_router)
router.include_router(employees_router)
router.include_router(add_employee_router)
router.include_router(invite_codes_router)
router.include_router(delete_router)
