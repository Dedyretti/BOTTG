"""Обработчики списка сотрудников."""

from aiogram import Router, F
from aiogram.types import Message
from sqlalchemy import select

from database.models import Employee
from bot.keyboards.admin.menu import get_employees_menu

router = Router()


@router.message(F.text == "📋 Список сотрудников")
async def list_employees(message: Message, session):
    """Показывает список сотрудников."""

    result = await session.execute(
        select(Employee).order_by(Employee.last_name)
    )
    employees = result.scalars().all()

    if not employees:
        await message.answer("Сотрудников пока нет")
        return

    text = "👥 <b>Список сотрудников:</b>\n\n"
    for emp in employees:
        if not emp.is_active:
            status = "🚫"
        elif emp.telegram_id:
            status = "✅"
        else:
            status = "⏳"

        role_icon = "👑" if emp.role in ("admin", "superuser") else "👤"
        active_text = "" if emp.is_active else " <i>(деактивирован)</i>"

        text += (
            f"{status} {role_icon} {emp.last_name} {emp.name}{active_text}\n"
            f"    📧 {emp.email}\n"
            f"    💼 {emp.position or 'Не указана'}\n\n"
        )

    await message.answer(text, reply_markup=get_employees_menu())
