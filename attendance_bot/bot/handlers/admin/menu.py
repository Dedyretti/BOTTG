from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from bot.keyboards.admin.menu import (
    admin_menu,
    employees_menu,
    requests_menu,
)
from bot.lexicon.lexicon import AdminMessages
from database.crud.employee import count_employees

router = Router()


@router.message(F.text == "📁 Заявки")
async def open_requests_menu(message: Message):
    """Открывает меню заявок."""
    await message.answer(
        AdminMessages.REQUESTS_MENU,
        reply_markup=requests_menu
    )


@router.message(F.text == "📊 Отчёты")
async def open_reports_menu(message: Message):
    """Открывает меню отчётов."""
    await message.answer(
        AdminMessages.REPORTS_IN_PROGRESS,
        reply_markup=admin_menu
    )


@router.message(F.text == "🔙 Главное меню")
async def back_to_main_menu(message: Message):
    """Возвращает в главное меню."""
    await message.answer(
        AdminMessages.MAIN_MENU_ADMIN,
        reply_markup=admin_menu
    )


@router.message(F.text == "❌ Отмена")
async def cancel_action(message: Message, state: FSMContext):
    """Отменяет текущее действие."""
    await state.clear()
    await message.answer(
        AdminMessages.ACTION_CANCELLED,
        reply_markup=admin_menu
    )


@router.message(F.text == "👥 Сотрудники")
async def open_employees_menu(message: Message, session):
    """Открывает меню управления сотрудниками."""
    total = await count_employees(session)

    await message.answer(
        AdminMessages.EMPLOYEES_COUNT.format(count=total),
        reply_markup=employees_menu
    )
