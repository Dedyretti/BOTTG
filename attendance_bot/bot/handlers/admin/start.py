from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from bot.keyboards.admin.menu import admin_menu
from bot.lexicon.lexicon import StartMessages
from core.logger import setup_logging
from database.crud.employee import get_employee_by_telegram_id

logger = setup_logging(__name__)
router = Router()


@router.message(CommandStart())
async def cmd_start_admin(message: Message, session):
    """Обрабатывает /start для админа."""

    employee = await get_employee_by_telegram_id(session, message.from_user.id)

    name = employee.name or "босс"
    await message.answer(
        StartMessages.WELCOME_ADMIN.format(name=name),
        reply_markup=admin_menu
    )

    logger.info(f"Админ {message.from_user.id} вызвал /start")
