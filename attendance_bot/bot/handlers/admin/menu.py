from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from sqlalchemy import select, func

from database.models import Employee
from bot.keyboards.admin.menu import admin_menu, get_employees_menu

router = Router()


@router.message(F.text == "🔙 Главное меню")
async def back_to_main(message: Message, state: FSMContext):
    """Возвращает в главное меню."""

    await state.clear()
    await message.answer("Главное меню:", reply_markup=admin_menu)


@router.message(F.text == "❌ Отмена")
async def cancel(message: Message, state: FSMContext):
    """Отменяет текущее действие."""

    await state.clear()
    await message.answer("Действие отменено", reply_markup=admin_menu)


@router.message(F.text == "👥 Сотрудники")
async def employees_menu(message: Message, session):
    """Открывает меню управления сотрудниками."""

    result = await session.execute(
        select(func.count(Employee.id))
    )
    total = result.scalar()

    await message.answer(
        f"👥 Сотрудников в системе: {total}",
        reply_markup=get_employees_menu()
    )


@router.message(F.text == "📊 Отчёты")
async def reports(message: Message):
    """Показывает меню отчётов."""
    await message.answer("📊 <b>Отчёты</b>\n\n🚧 В разработке")
