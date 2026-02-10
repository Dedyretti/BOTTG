from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy import select

from database.models import Employee, InviteCode
from database.enums import RoleEnum
from bot.keyboards.admin.menu import admin_menu, admin_cancel_menu
from bot.keyboards.admin.inline_keyboards import get_selection_role_keyboard
from bot.states.states_fsm import AddEmployeeStates

router = Router()


@router.message(F.text == "➕ Добавить сотрудника")
async def add_employee_start(message: Message, state: FSMContext):
    """Начинает процесс добавления сотрудника."""

    await state.set_state(AddEmployeeStates.waiting_name)
    await message.answer(
        "Введите <b>имя</b> сотрудника:",
        reply_markup=admin_cancel_menu
    )


@router.message(AddEmployeeStates.waiting_name)
async def process_name(message: Message, state: FSMContext):
    """Обрабатывает ввод имени."""

    await state.update_data(name=message.text.strip())
    await state.set_state(AddEmployeeStates.waiting_last_name)
    await message.answer("Введите <b>фамилию</b> сотрудника:")


@router.message(AddEmployeeStates.waiting_last_name)
async def process_last_name(message: Message, state: FSMContext):
    """Обрабатывает ввод фамилии."""

    await state.update_data(last_name=message.text.strip())
    await state.set_state(AddEmployeeStates.waiting_email)
    await message.answer("Введите <b>email</b> сотрудника:")


@router.message(AddEmployeeStates.waiting_email)
async def process_email(message: Message, state: FSMContext, session):
    """Обрабатывает ввод email."""

    email = message.text.strip().lower()

    result = await session.execute(
        select(Employee).where(Employee.email == email)
    )
    existing = result.scalar_one_or_none()

    if existing:
        await message.answer("❌ Сотрудник с таким email уже существует!")
        return

    await state.update_data(email=email)
    await state.set_state(AddEmployeeStates.waiting_position)
    await message.answer("Введите <b>должность</b> сотрудника:")


@router.message(AddEmployeeStates.waiting_position)
async def process_position(message: Message, state: FSMContext):
    """Обрабатывает ввод должности."""

    await state.update_data(position=message.text.strip())
    await state.set_state(AddEmployeeStates.waiting_role)
    await message.answer(
        "Выберите <b>роль</b> сотрудника:",
        reply_markup=get_selection_role_keyboard()
    )


@router.callback_query(F.data == "role:cancel")
async def cancel_role(callback: CallbackQuery, state: FSMContext):
    """Отменяет выбор роли."""
    await state.clear()
    await callback.message.edit_text("❌ Добавление сотрудника отменено")
    await callback.message.answer("Главное меню:", reply_markup=admin_menu)
    await callback.answer()


@router.callback_query(F.data.startswith("role:"))
async def process_role(callback: CallbackQuery, state: FSMContext, session):
    """Обрабатывает выбор роли и создаёт сотрудника."""

    role_value = callback.data.split(":")[1]

    if role_value == "user":
        role = RoleEnum.USER.value
    elif role_value == "admin":
        role = RoleEnum.ADMIN.value
    else:
        await callback.answer("Неверный выбор")
        return

    data = await state.get_data()

    employee = Employee(
        name=data["name"],
        last_name=data["last_name"],
        email=data["email"],
        position=data["position"],
        role=role,
        is_active=True
    )
    session.add(employee)
    await session.flush()

    invite_code = InviteCode(employee_id=employee.id)
    session.add(invite_code)
    await session.flush()
    await session.refresh(invite_code)

    await session.commit()

    await state.clear()
    await callback.message.edit_text(
        f"✅ <b>Сотрудник создан!</b>\n\n"
        f"👤 {employee.last_name} {employee.name}\n"
        f"📧 {employee.email}\n"
        f"💼 {employee.position}\n"
        f"🎭 Роль: {role}\n\n"
        f"🔑 <b>Инвайт-код:</b>\n"
        f"<code>{invite_code.code}</code>\n\n"
        f"⏰ Действителен до {invite_code.expires_at.strftime('%d.%m.%Y')}"
    )
    await callback.message.answer("Главное меню:", reply_markup=admin_menu)
    await callback.answer("Сотрудник создан!")
