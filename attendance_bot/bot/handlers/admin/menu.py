from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from sqlalchemy import select, func

from database.models import Employee
from bot.keyboards.admin.menu import (
    requests_menu,
    admin_menu,
    employees_menu
)

router = Router()


@router.message(F.text == "📁 Заявки")
async def open_requests_menu(message: Message):
    """Открыть меню заявок."""

    await message.answer(
        "📁 <b>Меню заявок</b>\n\n"
        "Выберите действие:",
        reply_markup=requests_menu
    )


@router.message(F.text == "👥 Сотрудники")
async def open_employees_menu(message: Message):
    """Открыть меню сотрудников."""

    await message.answer(
        "👥 <b>Меню сотрудников</b>\n\n"
        "Выберите действие:",
        reply_markup=employees_menu
    )


@router.message(F.text == "📊 Отчёты")
async def open_reports_menu(message: Message):
    """Открыть меню отчётов."""

    await message.answer(
        "📊 <b>Меню отчётов</b>\n\n"
        "Функционал в разработке...",
        reply_markup=admin_menu
    )


@router.message(F.text == "🔙 Главное меню")
async def back_to_main_menu(message: Message):
    """Вернуться в главное меню."""

    await message.answer(
        "🏠 <b>Главное меню администратора</b>",
        reply_markup=admin_menu
    )


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
async def get_employees_menu(message: Message, session):
    """Открывает меню управления сотрудниками."""

    result = await session.execute(
        select(func.count(Employee.id))
    )
    total = result.scalar()

    await message.answer(
        f"👥 Сотрудников в системе: {total}",
        reply_markup=employees_menu()
    )


@router.message(F.text == "📊 Отчёты")
async def reports(message: Message):
    """Показывает меню отчётов."""

    await message.answer("📊 <b>Отчёты</b>\n\n🚧 В разработке")
