from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from pydantic import EmailStr

from bot.keyboards.admin.inline_keyboards import (
    get_confirm_delete_keyboard,
    get_confirm_employee_keyboard,
    get_selection_role_keyboard,
)
from bot.keyboards.admin.menu import admin_cancel_menu, admin_menu
from bot.lexicon.lexicon import roles, AdminMessages
from bot.states.states_fsm import AddEmployeeStates, DeleteStates
from database.crud.employee import (
    create_employee,
    delete_employee_by_id,
    get_employee_by_email,
    get_employee_requests_count,
    list_employees,
)
from database.enums import RoleEnum
from schemas.employee import EmployeeCreate

router = Router()


def _format_employee_preview(data: dict) -> str:
    """Форматирует превью данных сотрудника."""
    role_name = roles.get(data["role"], data["role"])

    return AdminMessages.ADD_EMPLOYEE_PREVIEW.format(
        name=data["name"],
        last_name=data["last_name"],
        email=data["email"],
        position=data.get("position") or "не указана",
        role=role_name
    )


def _format_employee_info(employee) -> str:
    """Форматирует информацию о сотруднике."""
    role_name = roles.get(employee.role, employee.role)

    return AdminMessages.EMPLOYEE_INFO.format(
        full_name=f"{employee.last_name} {employee.name}",
        email=employee.email,
        position=employee.position or "Не указана",
        role=role_name
    )


@router.message(F.text == "➕ Добавить сотрудника")
async def add_employee_start(message: Message, state: FSMContext):
    """Начинает процесс добавления сотрудника."""
    await state.set_state(AddEmployeeStates.waiting_name)
    await message.answer(
        AdminMessages.ADD_EMPLOYEE_START,
        reply_markup=admin_cancel_menu
    )


@router.message(AddEmployeeStates.waiting_name)
async def process_name(message: Message, state: FSMContext):
    """Обрабатывает ввод имени."""
    name = message.text.strip()

    if len(name) < 2:
        await message.answer(AdminMessages.ERROR_NAME_TOO_SHORT)
        return

    await state.update_data(name=name)
    await state.set_state(AddEmployeeStates.waiting_last_name)
    await message.answer(AdminMessages.ADD_EMPLOYEE_LAST_NAME)


@router.message(AddEmployeeStates.waiting_last_name)
async def process_last_name(message: Message, state: FSMContext):
    """Обрабатывает ввод фамилии."""
    last_name = message.text.strip()

    if len(last_name) < 2:
        await message.answer(AdminMessages.ERROR_LAST_NAME_TOO_SHORT)
        return

    await state.update_data(last_name=last_name)
    await state.set_state(AddEmployeeStates.waiting_email)
    await message.answer(AdminMessages.ADD_EMPLOYEE_EMAIL)


@router.message(AddEmployeeStates.waiting_email)
async def process_email(message: Message, state: FSMContext, session):
    """Обрабатывает ввод email."""
    email = message.text.strip().lower()

    try:
        EmailStr._validate(email)
    except Exception:
        await message.answer(AdminMessages.ERROR_INVALID_EMAIL)
        return

    existing = await get_employee_by_email(session, email)
    if existing:
        await message.answer(AdminMessages.ERROR_EMAIL_EXISTS)
        return

    await state.update_data(email=email)
    await state.set_state(AddEmployeeStates.waiting_position)
    await message.answer(AdminMessages.ADD_EMPLOYEE_POSITION)


@router.message(AddEmployeeStates.waiting_position)
async def process_position(message: Message, state: FSMContext):
    """Обрабатывает ввод должности."""
    await state.update_data(position=message.text.strip())
    await state.set_state(AddEmployeeStates.waiting_role)
    await message.answer(
        AdminMessages.ADD_EMPLOYEE_ROLE,
        reply_markup=get_selection_role_keyboard()
    )


@router.callback_query(F.data == "role:cancel")
async def cancel_role(callback: CallbackQuery, state: FSMContext):
    """Отменяет выбор роли."""
    await state.clear()
    await callback.message.edit_text(AdminMessages.ADD_EMPLOYEE_CANCELLED)
    await callback.message.answer(
        AdminMessages.MAIN_MENU,
        reply_markup=admin_menu
    )
    await callback.answer()


@router.callback_query(
    F.data.startswith("role:"),
    AddEmployeeStates.waiting_role
)
async def process_role_selection(callback: CallbackQuery, state: FSMContext):
    """Обрабатывает выбор роли."""
    role = callback.data.split(":")[1]

    if role == "cancel":
        await cancel_role(callback, state)
        return

    await state.update_data(role=role)
    await state.set_state(AddEmployeeStates.confirming)

    data = await state.get_data()

    await callback.message.edit_text(
        _format_employee_preview(data),
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
    """Подтверждает создание сотрудника."""
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

        full_name = f"{employee.last_name} {employee.name}"
        role_name = roles.get(employee.role, employee.role)

        if employee.invite_codes:
            invite_code = employee.invite_codes[0].code
            success_text = AdminMessages.ADD_EMPLOYEE_SUCCESS_WITH_CODE.format(
                full_name=full_name,
                email=employee.email,
                role=role_name,
                invite_code=invite_code
            )
        else:
            success_text = AdminMessages.ADD_EMPLOYEE_SUCCESS.format(
                full_name=full_name,
                email=employee.email,
                role=role_name
            )

        await callback.message.edit_text(success_text)
        await callback.answer("✅ Сотрудник создан")

    except ValueError as e:
        await callback.message.edit_text(
            AdminMessages.ERROR_GENERIC.format(error=str(e))
        )
        await callback.answer()

    await state.clear()
    await callback.message.answer(
        AdminMessages.MAIN_MENU,
        reply_markup=admin_menu
    )


@router.callback_query(
    F.data == "employee:cancel",
    AddEmployeeStates.confirming
)
async def cancel_create_employee(callback: CallbackQuery, state: FSMContext):
    """Отменяет создание сотрудника."""
    await state.clear()
    await callback.message.edit_text(AdminMessages.ADD_EMPLOYEE_CANCELLED)
    await callback.message.answer(
        AdminMessages.MAIN_MENU,
        reply_markup=admin_menu
    )
    await callback.answer()


@router.message(F.text == "📋 Список сотрудников")
async def list_all_employees(message: Message, session):
    """Показывает всех сотрудников."""
    employees = await list_employees(session)

    if not employees:
        await message.answer(AdminMessages.EMPLOYEE_LIST_EMPTY)
        return

    text = AdminMessages.EMPLOYEE_LIST_HEADER

    for emp in employees:
        text += _format_employee_info(emp) + "\n\n"

    await message.answer(text)


@router.message(F.text == "🗑 Удалить сотрудника")
async def delete_start(message: Message, state: FSMContext):
    """Начинает процесс удаления сотрудника."""
    await state.set_state(DeleteStates.waiting_email)
    await message.answer(
        AdminMessages.DELETE_START,
        reply_markup=admin_cancel_menu
    )


@router.message(DeleteStates.waiting_email)
async def process_delete_email(message: Message, state: FSMContext, session):
    """Ищет сотрудника для удаления."""
    email = message.text.strip().lower()

    employee = await get_employee_by_email(session, email)

    if not employee:
        await message.answer(AdminMessages.DELETE_NOT_FOUND)
        return

    if employee.role == "superuser":
        await state.clear()
        await message.answer(
            AdminMessages.DELETE_SUPERUSER_FORBIDDEN,
            reply_markup=admin_menu
        )
        return

    requests_count = await get_employee_requests_count(session, employee.id)

    await state.update_data(employee_id=employee.id)
    await state.set_state(DeleteStates.confirming)

    await message.answer(
        AdminMessages.DELETE_CONFIRM.format(
            full_name=f"{employee.last_name} {employee.name}",
            email=employee.email,
            requests_count=requests_count
        ),
        reply_markup=get_confirm_delete_keyboard(employee.id)
    )


@router.callback_query(F.data == "delete_cancel")
async def cancel_delete(callback: CallbackQuery, state: FSMContext):
    """Отменяет удаление."""
    await state.clear()
    await callback.message.edit_text(AdminMessages.DELETE_CANCELLED)
    await callback.message.answer(
        AdminMessages.MAIN_MENU,
        reply_markup=admin_menu
    )
    await callback.answer()


@router.callback_query(F.data.startswith("delete_confirm:"))
async def confirm_delete(
    callback: CallbackQuery,
    state: FSMContext,
    session
):
    """Подтверждает удаление сотрудника."""
    employee_id = int(callback.data.split(":")[1])

    employee = await delete_employee_by_id(session, employee_id)

    if not employee:
        await callback.message.edit_text(
            AdminMessages.DELETE_NOT_FOUND_ON_CONFIRM
        )
        await state.clear()
        await callback.answer()
        return

    await state.clear()

    await callback.message.edit_text(
        AdminMessages.DELETE_SUCCESS.format(
            full_name=f"{employee.last_name} {employee.name}",
            email=employee.email
        )
    )
    await callback.message.answer(
        AdminMessages.MAIN_MENU,
        reply_markup=admin_menu
    )
    await callback.answer("Удалено")
