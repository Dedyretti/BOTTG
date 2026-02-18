from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from bot.keyboards.admin.menu import admin_cancel_menu, admin_menu
from bot.lexicon.lexicon import AdminMessages
from bot.states.states_fsm import InviteCodeStates
from database.crud.employee import get_employee_by_email
from database.crud.invite_code import (
    create_invite_code,
    deactivate_old_invite_codes,
    get_active_invite_code,
)

router = Router()


def _format_datetime(dt) -> str:
    """Форматирует datetime для отображения."""
    return dt.strftime('%d.%m.%Y %H:%M')


@router.message(F.text == "🔑 Создать инвайт-код")
async def create_invite_start(message: Message, state: FSMContext):
    """Начинает процесс создания инвайт-кода."""
    await state.set_state(InviteCodeStates.waiting_email)
    await message.answer(
        AdminMessages.INVITE_START,
        reply_markup=admin_cancel_menu
    )


@router.message(InviteCodeStates.waiting_email)
async def process_invite_email(message: Message, state: FSMContext, session):
    """Ищет сотрудника и создаёт/обновляет инвайт-код."""
    email = message.text.strip().lower()

    employee = await get_employee_by_email(session, email)

    if not employee:
        await message.answer(AdminMessages.INVITE_EMPLOYEE_NOT_FOUND)
        return

    full_name = f"{employee.last_name} {employee.name}"

    if employee.telegram_id:
        await state.clear()
        await message.answer(
            AdminMessages.INVITE_ALREADY_LINKED.format(full_name=full_name),
            reply_markup=admin_menu
        )
        return

    existing_code = await get_active_invite_code(session, employee.id)

    if existing_code:
        await state.clear()
        await message.answer(
            AdminMessages.INVITE_CODE_EXISTS.format(
                code=existing_code.code,
                expires_at=_format_datetime(existing_code.expires_at)
            ),
            reply_markup=admin_menu
        )
        return

    await deactivate_old_invite_codes(session, employee.id)

    new_code = await create_invite_code(session, employee.id)

    await session.commit()

    await state.clear()
    await message.answer(
        AdminMessages.INVITE_CODE_CREATED.format(
            full_name=full_name,
            email=employee.email,
            code=new_code.code,
            expires_at=_format_datetime(new_code.expires_at)
        ),
        reply_markup=admin_menu
    )
