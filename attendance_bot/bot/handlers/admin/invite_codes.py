from datetime import datetime, timezone

from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from sqlalchemy import select

from database.models import Employee, InviteCode
from bot.keyboards.admin.menu import admin_menu, admin_cancel_menu
from bot.states.states_fsm import InviteCodeStates

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

    result = await session.execute(
        select(InviteCode).where(
            InviteCode.employee_id == employee.id,
            not InviteCode.is_used,
            InviteCode.expires_at > datetime.now(timezone.utc)
        )
    )
    existing_code = result.scalar_one_or_none()

    if existing_code:
        await state.clear()
        await message.answer(
            f"ℹ️ У сотрудника уже есть активный инвайт-код:\n\n"
            f"🔑 <code>{existing_code.code}</code>\n"
            f"⏰ До {existing_code.expires_at.strftime('%d.%m.%Y %H:%M')}",
            reply_markup=admin_menu
        )
        return

    result = await session.execute(
        select(InviteCode).where(
            InviteCode.employee_id == employee.id,
            not InviteCode.is_used
        )
    )
    old_codes = result.scalars().all()
    for old_code in old_codes:
        old_code.is_used = True

    new_code = InviteCode(employee_id=employee.id)
    session.add(new_code)
    await session.flush()
    await session.refresh(new_code)

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
