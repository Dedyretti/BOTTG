from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from bot.keyboards.user.reply_keyboards import user_menu
from bot.lexicon.lexicon import StartMessages
from core.logger import setup_logging
from database.crud.employee import get_employee_by_telegram_id

logger = setup_logging(__name__)
router = Router()


@router.message(CommandStart())
async def cmd_start_user(message: Message, session):
    """Обрабатывает /start для верифицированного пользователя."""

    employee = await get_employee_by_telegram_id(session, message.from_user.id)

    name = employee.name or "друг"
    await message.answer(
        StartMessages.WELCOME_BACK.format(name=name),
        reply_markup=user_menu
    )

    logger.info(f"Пользователь {message.from_user.id} вызвал /start")
