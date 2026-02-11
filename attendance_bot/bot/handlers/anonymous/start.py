from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from bot.lexicon.lexicon import StartMessages
from bot.states.states_fsm import RegisterStates
from core.logger import setup_logging

logger = setup_logging(__name__)
router = Router()


@router.message(CommandStart())
async def cmd_start_anonymous(message: Message, state: FSMContext):
    """Обрабатывает /start для анонимного пользователя."""

    await state.set_state(RegisterStates.waiting_email)
    await message.answer(StartMessages.HELLO_ANONYMOUS)

    logger.info(f"Аноним {message.from_user.id} начал регистрацию")
