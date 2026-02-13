from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from pydantic import EmailStr
from sqlalchemy import select

from bot.keyboards.admin.inline_keyboards import (
    get_confirm_delete_keyboard,
    get_selection_role_keyboard,
    get_confirm_employee_keyboard,
)

from bot.lexicon.lexicon import roles
from bot.keyboards.admin.menu import admin_cancel_menu, admin_menu
from bot.states.states_fsm import AddEmployeeStates, DeleteStates
from database.crud.employee import (
    create_employee,
    get_employee_by_email,
    list_employees,
)
from database.enums import RoleEnum
from database.models import AbsenceRequest, Employee
from schemas.employee import EmployeeCreate

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

    name = message.text.strip()

    if len(name) < 2:
        await message.answer("❌ Имя должно быть не менее 2 символов")
        return

    await state.update_data(name=name)
    await state.set_state(AddEmployeeStates.waiting_last_name)
    await message.answer("Введите <b>фамилию</b> сотрудника:")


@router.message(AddEmployeeStates.waiting_last_name)
async def process_last_name(message: Message, state: FSMContext):
    """Обрабатывает ввод фамилии."""

    last_name = message.text.strip()

    if len(last_name) < 2:
        await message.answer("❌ Фамилия должна быть не менее 2 символов")
        return

    await state.update_data(last_name=last_name)
    await state.set_state(AddEmployeeStates.waiting_email)
    await message.answer("Введите <b>email</b> сотрудника:")


@router.message(AddEmployeeStates.waiting_email)
async def process_email(message: Message, state: FSMContext, session):
    """Обрабатывает ввод email."""

    email = message.text.strip().lower()

    try:
        EmailStr._validate(email)
    except Exception:
        await message.answer(
            "❌ Некорректный email!\n"
            "Введите email в формате: example@domain.com"
        )
        return

    existing = await get_employee_by_email(session, email)
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


@router.callback_query(
    F.data.startswith("role:"),
    AddEmployeeStates.waiting_role
)
async def process_role_selection(
    callback: CallbackQuery,
    state: FSMContext
):
    """Обработка выбора роли и показ подтверждения."""

    role = callback.data.split(":")[1]

    if role == "cancel":
        await state.clear()
        await callback.message.edit_text("❌ Добавление сотрудника отменено")
        await callback.message.answer(
            "Главное меню:",
            reply_markup=admin_menu
        )
        await callback.answer()
        return

    await state.update_data(role=role)
    await state.set_state(AddEmployeeStates.confirming)

    data = await state.get_data()
    role_name = roles.get(role, role)

    await callback.message.edit_text(
        "📋 <b>Проверьте данные нового сотрудника:</b>\n\n"
        f"👤 <b>Имя:</b> {data['name']}\n"
        f"👤 <b>Фамилия:</b> {data['last_name']}\n"
        f"📧 <b>Email:</b> {data['email']}\n"
        f"💼 <b>Должность:</b> {data.get('position') or 'не указана'}\n"
        f"🎭 <b>Роль:</b> {role_name}\n\n"
        "Всё верно?",
        reply_markup=get_confirm_employee_keyboard()
    )
    await callback.answer()


@router.callback_query(
    F.data == "employee:confirm",
    AddEmployeeStates.confirming
)
async def confirm_create_employee(
    callback: CallbackQuery,
    state: FSMContext,
    session
):
    """Подтвердить создание сотрудника."""

    data = await state.get_data()

    employee_data = EmployeeCreate(
        name=data["name"],
        last_name=data["last_name"],
        email=data["email"],
        position=data.get("position"),
        patronymic=None
    )

    try:
        role_enum = RoleEnum(data["role"])
        employee = await create_employee(
            session,
            employee_data,
            role=role_enum
        )

        invite_code = None
        if employee.invite_codes:
            invite_code = employee.invite_codes[0].code

        success_text = (
            "✅ <b>Сотрудник успешно добавлен!</b>\n\n"
            f"👤 {employee.last_name} {employee.name}\n"
            f"📧 {employee.email}\n"
            f"🎭 Роль: {roles.get(employee.role, employee.role)}\n"
        )

        if invite_code:
            success_text += (
                f"\n🔑 <b>Инвайт-код:</b>\n"
                f"<code>{invite_code}</code>"
            )

        await callback.message.edit_text(success_text)
        await callback.message.answer(
            "Главное меню:",
            reply_markup=admin_menu
        )

    except ValueError as e:
        await callback.message.edit_text(f"❌ Ошибка: {str(e)}")
        await callback.message.answer(
            "Главное меню:",
            reply_markup=admin_menu
        )

    await state.clear()
    await callback.answer("✅ Сотрудник создан")


@router.callback_query(
    F.data == "employee:edit",
    AddEmployeeStates.confirming
)
async def edit_employee_data(callback: CallbackQuery, state: FSMContext):
    """Начать редактирование данных сотрудника."""

    await state.set_state(AddEmployeeStates.waiting_name)
    await callback.message.edit_text(
        "✏️ <b>Редактирование данных</b>\n\n"
        "Введите <b>имя</b> сотрудника:"
    )
    await callback.answer()


@router.callback_query(
    F.data == "employee:cancel",
    AddEmployeeStates.confirming
)
async def cancel_create_employee(callback: CallbackQuery, state: FSMContext):
    """Отменить создание сотрудника."""

    await state.clear()
    await callback.message.edit_text("❌ Добавление сотрудника отменено")
    await callback.message.answer(
        "Главное меню:",
        reply_markup=admin_menu
    )
    await callback.answer()


@router.message(F.text == "📋 Список сотрудников")
async def list_all_employees(message: Message, session):
    """Показывает всех сотрудников в бд"""

    employees = await list_employees(session)
    if not employees:
        await message.answer("✨ Нет сотрудников в системе")
        return
    text = "📋 <b>Список сотрудников:</b>\n\n"
    for emp in employees:
        text += (f"👤 <b> {emp.last_name} {emp.name}</b>\n"
                 f"📧 {emp.email}\n"
                 f"💼 {emp.position or 'Не указана'}\n"
                 f"🎭 Роль: {roles[emp.role]}\n\n"
                 )

    await message.answer(text)


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
