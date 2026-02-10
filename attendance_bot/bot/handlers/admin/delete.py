from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy import select

from database.models import Employee, AbsenceRequest
from bot.keyboards.admin.menu import admin_menu, admin_cancel_menu
from bot.keyboards.admin.inline_keyboards import get_confirm_delete_keyboard
from bot.states.states_fsm import DeleteStates

router = Router()


@router.message(F.text == "🗑 Удалить сотрудника")
async def delete_start(message: Message, state: FSMContext):
    """Начинает процесс удаления сотрудника."""

    await state.set_state(DeleteStates.waiting_email)
    await message.answer(
        "🗑 <b>Удаление сотрудника</b>\n\n"
        "⚠️ <b>Внимание!</b> Это действие необратимо.\n"
        "Будут удалены все данные сотрудника.\n\n"
        "Введите <b>email</b> сотрудника:",
        reply_markup=admin_cancel_menu
    )


@router.message(DeleteStates.waiting_email)
async def process_delete_email(message: Message, state: FSMContext, session):
    """Ищет сотрудника для удаления."""

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

    if employee.role == "superuser":
        await state.clear()
        await message.answer(
            "❌ Нельзя удалить суперпользователя.",
            reply_markup=admin_menu
        )
        return

    result = await session.execute(
        select(AbsenceRequest).where(AbsenceRequest.employee_id == employee.id)
    )
    requests_count = len(result.scalars().all())

    await state.update_data(employee_id=employee.id)
    await state.set_state(DeleteStates.confirming)

    await message.answer(
        f"⚠️ <b>Подтверждение удаления</b>\n\n"
        f"👤 {employee.last_name} {employee.name}\n"
        f"📧 {employee.email}\n"
        f"📋 Заявок: {requests_count}\n\n"
        f"<b>Удалить этого сотрудника?</b>",
        reply_markup=get_confirm_delete_keyboard(employee.id)
    )


@router.callback_query(F.data == "delete_cancel")
async def cancel_delete(callback: CallbackQuery, state: FSMContext):
    """Отменяет удаление."""

    await state.clear()
    await callback.message.edit_text("❌ Удаление отменено")
    await callback.message.answer("Главное меню:", reply_markup=admin_menu)
    await callback.answer()


@router.callback_query(F.data.startswith("delete_confirm:"))
async def confirm_delete(callback: CallbackQuery, state: FSMContext, session):
    """Подтверждает удаление сотрудника."""

    employee_id = int(callback.data.split(":")[1])

    employee = await session.get(Employee, employee_id)

    if not employee:
        await callback.message.edit_text("❌ Сотрудник не найден")
        await state.clear()
        await callback.answer()
        return

    name = f"{employee.last_name} {employee.name}"
    email = employee.email

    await session.delete(employee)
    await session.commit()

    await state.clear()
    await callback.message.edit_text(
        f"✅ <b>Сотрудник удалён</b>\n\n"
        f"👤 {name}\n"
        f"📧 {email}"
    )
    await callback.message.answer("Главное меню:", reply_markup=admin_menu)
    await callback.answer("Удалено")
