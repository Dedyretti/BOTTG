from uuid import UUID

from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from bot.lexicon.lexicon import RegisterMessages, RoleNames
from bot.states.states_fsm import RegisterStates
from core.logger import setup_logging
from database.crud.employee import (
    bind_telegram_to_employee,
    get_employee_by_email,
    get_employee_by_id,
)
from database.crud.invite_code import (
    check_invite_code_status,
    format_invite_expiry,
    get_invite_code_for_employee,
    mark_invite_code_used,
)
from bot.utils.utils import get_menu_by_role

logger = setup_logging(__name__)

router = Router()


@router.message(RegisterStates.waiting_email)
async def process_email_start(message: Message, state: FSMContext, session):
    """Начало процесса регистрации - запрос email."""

    await process_email(message, state, session)


@router.message(RegisterStates.waiting_email)
async def process_email(message: Message, state: FSMContext, session):
    """Обрабатывает ввод email."""

    email = message.text.strip().lower()
    employee = await get_employee_by_email(session, email)

    if not employee:
        await message.answer(RegisterMessages.EMAIL_NOT_FOUND)
        return

    await state.update_data(employee_id=employee.id)
    await state.set_state(RegisterStates.waiting_code)
    await message.answer(RegisterMessages.ENTER_CODE)


@router.message(RegisterStates.waiting_code)
async def process_code(message: Message, state: FSMContext, session):
    """Обрабатывает ввод инвайт-кода."""

    code_str = message.text.strip()

    try:
        code_uuid = UUID(code_str)
    except ValueError:
        logger.warning(
            f"Невалидный UUID от {message.from_user.id}: {code_str!r}"
        )
        await message.answer(
            RegisterMessages.INVALID_CODE_FORMAT,
            parse_mode="HTML"
        )
        return

    data = await state.get_data()
    employee_id = data["employee_id"]

    invite = await get_invite_code_for_employee(
        session,
        employee_id,
        code_uuid
        )

    if not invite:
        await message.answer(RegisterMessages.CODE_NOT_FOUND)
        return

    status = check_invite_code_status(invite)

    if status == "used":
        await message.answer(RegisterMessages.CODE_ALREADY_USED)
        return

    if status == "expired":
        expires = format_invite_expiry(invite.expires_at)
        await message.answer(
            RegisterMessages.CODE_EXPIRED.format(expires=expires)
        )
        return

    await bind_telegram_to_employee(session, employee_id, message.from_user.id)
    await mark_invite_code_used(session, code_uuid)

    employee = await get_employee_by_id(session, employee_id)
    role_text = RoleNames.get(employee.role)

    await message.answer(
        RegisterMessages.SUCCESS.format(role=role_text),
        reply_markup=get_menu_by_role(employee.role),
        parse_mode="HTML"
    )

    logger.info(
        f"Зарегистрирован: tg={message.from_user.id}, "
        f"employee_id={employee_id}"
    )
    await state.clear()
