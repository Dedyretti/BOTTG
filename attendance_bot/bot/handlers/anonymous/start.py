from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

from bot.lexicon.lexicon import StartMessages
from core.logger import setup_logging
from bot.keyboards.anonymous.anonymous_keyboards import get_activation_keyboard
from bot.states.states_fsm import RegisterStates

logger = setup_logging(__name__)
router = Router()


@router.message(CommandStart())
async def cmd_start_anonymous(message: Message, state: FSMContext):
    """Обрабатывает /start для анонимного пользователя."""

    await message.answer(StartMessages.HELLO_ANONYMOUS,
                         reply_markup=get_activation_keyboard())

    logger.info(f"Аноним {message.from_user.id} начал регистрацию")


@router.callback_query(F.data == "activate_account")
async def process_activation_callback(callback: CallbackQuery,
                                      state: FSMContext):
    """Обрабатывает нажатие на кнопку активации."""

    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.answer()
    await state.set_state(RegisterStates.waiting_email)
    await callback.message.answer(StartMessages.WAIT_EMAIL_USERS)

    logger.info(f"Пользователь {callback.from_user.id} начал ввод email")
