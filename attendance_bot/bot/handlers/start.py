from datetime import datetime, timezone
from uuid import UUID
from core.logger import setup_logging

from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy import select

from bot.keyboards.admin.menu import admin_menu
from bot.keyboards.user.menu import user_menu
from database.models import Employee, InviteCode
from bot.states.states_fsm import RegisterStates

logger = setup_logging(__name__)


def get_main_menu(role: str = "user"):
    """Возвращает клавиатуру главного меню в зависимости от роли."""

    if role in ("admin", "superuser"):
        logger.info("Показ главного меню для администратора")
        return admin_menu
    logger.info("Показ главного меню для пользователя")
    return user_menu


router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, session):
    """Обрабатывает команду /start."""

    result = await session.execute(
        select(Employee).where(Employee.telegram_id == message.from_user.id)
    )
    employee = result.scalar_one_or_none()

    if employee:
        await message.answer(
            f"С возвращением, {employee.name or 'друг'}!",
            reply_markup=get_main_menu(employee.role)
        )
        logger.info("Пользователь уже зарегистрирован, показ главного меню")
        return

    await state.set_state(RegisterStates.waiting_email)
    logger.info("Новый пользователь, начало регистрации")
    await message.answer("Привет! Введи свой рабочий email:")


@router.message(RegisterStates.waiting_email)
async def process_email(message: Message, state: FSMContext, session):
    """Обрабатывает ввод email пользователем."""

    email = message.text.strip().lower()
    await state.update_data(email=email)

    result = await session.execute(
        select(Employee).where(Employee.email == email)
    )
    employee = result.scalar_one_or_none()

    if not employee:
        await message.answer("Сотрудник с таким email не найден.")
        return

    await state.update_data(employee_id=employee.id)
    await state.set_state(RegisterStates.waiting_code)
    await message.answer("Отлично! Теперь введи инвайт-код:")


@router.message(RegisterStates.waiting_code)
async def process_code(message: Message, state: FSMContext, session):
    """Обрабатывает ввод инвайт-кода и завершает регистрацию."""

    code = message.text.strip()
    data = await state.get_data()
    employee_id = data["employee_id"]

    result = await session.execute(
        select(InviteCode).where(
            InviteCode.employee_id == employee_id,
            InviteCode.code == UUID(code),
            InviteCode.is_used.is_(False)
        )
    )
    invite = result.scalar_one_or_none()

    if not invite:
        await message.answer("Неверный или уже использованный код.")
        return

    employee = await session.get(Employee, employee_id)
    employee.telegram_id = message.from_user.id
    invite.is_used = True
    invite.used_at = datetime.now(timezone.utc)

    logger.info("Пользователь успешно зарегистрирован, сохранение данных в БД")
    await session.commit()

    role_text = "админ" if employee.role in ("admin",
                                             "superuser") else "сотрудник"
    await message.answer(
        f"Привязка успешна!\nРоль: {role_text}",
        reply_markup=get_main_menu(employee.role)
    )
    await state.clear()
