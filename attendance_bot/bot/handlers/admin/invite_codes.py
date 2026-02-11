from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy import select

from bot.keyboards.admin.menu import admin_cancel_menu, admin_menu
from bot.states.states_fsm import InviteCodeStates
from database.crud.invite_code import (
    create_invite_code,
    deactivate_old_invite_codes,
    get_active_invite_code,
)
from database.models import Employee

router = Router()


@router.message(F.text == "🔑 Создать инвайт-код")
async def create_invite_start(message: Message, state: FSMContext):
    """Начинает процесс создания инвайт-кода."""

    await state.set_state(InviteCodeStates.waiting_email)
    await message.answer(
        "🔑 <b>Создание инвайт-кода</b>\n\n"
        "Введите <b>email</b> сотрудника:",
        reply_markup=admin_cancel_menu
    )


@router.message(InviteCodeStates.waiting_email)
async def process_invite_email(message: Message, state: FSMContext, session):
    """Ищет сотрудника и создаёт/обновляет инвайт-код."""

    email = message.text.strip().lower()

    # Поиск сотрудника
    result = await session.execute(
        select(Employee).where(Employee.email == email)
    )
    employee = result.scalar_one_or_none()

    if not employee:
        await message.answer(
            "❌ Сотрудник с таким email не найден.\n"
            "Попробуйте ещё раз или нажмите Отмена."
        )
        return

    if employee.telegram_id:
        await state.clear()
        await message.answer(
            f"ℹ️ Сотрудник <b>{employee.last_name} {employee.name}</b> "
            f"уже привязан к Telegram.\n\n"
            f"Новый инвайт-код не требуется.",
            reply_markup=admin_menu
        )
        return

    existing_code = await get_active_invite_code(session, employee.id)

    if existing_code:
        await state.clear()
        await message.answer(
            f"ℹ️ У сотрудника уже есть активный инвайт-код:\n\n"
            f"🔑 <code>{existing_code.code}</code>\n"
            f"⏰ До {existing_code.expires_at.strftime('%d.%m.%Y %H:%M')}",
            reply_markup=admin_menu
        )
        return

    await deactivate_old_invite_codes(session, employee.id)

    new_code = await create_invite_code(session, employee.id)

    await session.commit()

    await state.clear()
    await message.answer(
        f"✅ <b>Инвайт-код создан!</b>\n\n"
        f"👤 {employee.last_name} {employee.name}\n"
        f"📧 {employee.email}\n\n"
        f"🔑 <b>Новый инвайт-код:</b>\n"
        f"<code>{new_code.code}</code>\n\n"
        f"⏰ Действителен до {new_code.expires_at.strftime('%d.%m.%Y %H:%M')}",
        reply_markup=admin_menu
    )
