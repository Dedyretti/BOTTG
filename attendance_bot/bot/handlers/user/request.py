from datetime import date

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy import select

from database.models import Employee, AbsenceRequest, AbsenceRequestHistory
from database.enums import RequestStatusEnum, ChangeTypeEnum
from bot.keyboards.user.request import (
    get_request_type_keyboard,
    get_confirm_keyboard,
    get_cancel_keyboard,
    REQUEST_TYPE_LABELS
)
from bot.keyboards.user.calendar import (
    get_calendar_keyboard,
    get_prev_month,
    get_next_month
)
from bot.states.states_fsm import CreateRequestStates
from bot.keyboards.admin.menu import admin_menu
from bot.keyboards.user.menu import user_menu

router = Router()


@router.message(F.text == "📝 Подать заявку")
async def start_request(message: Message, state: FSMContext):
    """Начинает процесс создания заявки."""

    await state.set_state(CreateRequestStates.choosing_type)
    await message.answer(
        "📝 <b>Новая заявка</b>\n\n"
        "Выберите тип отсутствия:",
        reply_markup=get_request_type_keyboard()
    )


async def get_menu_by_role(session, telegram_id):
    """Возвращает меню в зависимости от роли пользователя."""
    result = await session.execute(
        select(Employee).where(Employee.telegram_id == telegram_id)
    )
    employee = result.scalar_one_or_none()

    if employee and employee.role in ("admin", "superuser"):
        return admin_menu
    return user_menu


@router.callback_query(F.data == "req_cancel")
async def cancel_request(callback: CallbackQuery, state: FSMContext, session):
    """Отменяет создание заявки."""
    await state.clear()
    await callback.message.edit_text("❌ Создание заявки отменено")

    menu = await get_menu_by_role(session, callback.from_user.id)
    await callback.message.answer("Главное меню:", reply_markup=menu)
    await callback.answer()


@router.callback_query(F.data.startswith("req_type:"))
async def process_type(callback: CallbackQuery, state: FSMContext):
    """Обрабатывает выбор типа отсутствия."""

    request_type = callback.data.split(":")[1]
    await state.update_data(request_type=request_type)

    type_name = REQUEST_TYPE_LABELS.get(request_type, request_type)
    await callback.message.edit_text(
        f"📝 <b>Новая заявка</b>\n\n"
        f"Тип: {type_name}\n\n"
        f"📅 Выберите <b>дату начала</b>:",
        reply_markup=get_calendar_keyboard(prefix="start")
    )
    await state.set_state(CreateRequestStates.entering_start_date)
    await callback.answer()


@router.callback_query(F.data.startswith("start:prev:"))
async def start_prev_month(callback: CallbackQuery):
    """Предыдущий месяц для даты начала."""

    _, _, year, month = callback.data.split(":")
    new_year, new_month = get_prev_month(int(year), int(month))
    await callback.message.edit_reply_markup(
        reply_markup=get_calendar_keyboard(new_year, new_month, prefix="start")
    )
    await callback.answer()


@router.callback_query(F.data.startswith("start:next:"))
async def start_next_month(callback: CallbackQuery):
    """Следующий месяц для даты начала."""

    _, _, year, month = callback.data.split(":")
    new_year, new_month = get_next_month(int(year), int(month))
    await callback.message.edit_reply_markup(
        reply_markup=get_calendar_keyboard(new_year, new_month, prefix="start")
    )
    await callback.answer()


@router.callback_query(F.data.startswith("start:day:"))
async def process_start_date(callback: CallbackQuery, state: FSMContext):
    """Обрабатывает выбор даты начала."""

    _, _, year, month, day = callback.data.split(":")
    start_date = date(int(year), int(month), int(day))

    await state.update_data(start_date=start_date.isoformat())

    data = await state.get_data()
    type_name = REQUEST_TYPE_LABELS.get(data["request_type"],
                                        data["request_type"])

    await callback.message.edit_text(
        f"📝 <b>Новая заявка</b>\n\n"
        f"Тип: {type_name}\n"
        f"📅 Начало: <b>{start_date.strftime('%d.%m.%Y')}</b>\n\n"
        f"📅 Выберите <b>дату окончания</b>:",
        reply_markup=get_calendar_keyboard(int(year), int(month), prefix="end")
    )
    await state.set_state(CreateRequestStates.entering_end_date)
    await callback.answer()


@router.callback_query(F.data.startswith("start:ignore"))
async def ignore_start(callback: CallbackQuery):
    """Игнорирует нажатие на неактивную кнопку."""

    await callback.answer()


@router.callback_query(F.data.startswith("end:prev:"))
async def end_prev_month(callback: CallbackQuery):
    """Предыдущий месяц для даты окончания."""

    _, _, year, month = callback.data.split(":")
    new_year, new_month = get_prev_month(int(year), int(month))
    await callback.message.edit_reply_markup(
        reply_markup=get_calendar_keyboard(new_year, new_month, prefix="end")
    )
    await callback.answer()


@router.callback_query(F.data.startswith("end:next:"))
async def end_next_month(callback: CallbackQuery):
    """Следующий месяц для даты окончания."""

    _, _, year, month = callback.data.split(":")
    new_year, new_month = get_next_month(int(year), int(month))
    await callback.message.edit_reply_markup(
        reply_markup=get_calendar_keyboard(new_year, new_month, prefix="end")
    )
    await callback.answer()


@router.callback_query(F.data.startswith("end:day:"))
async def process_end_date(callback: CallbackQuery, state: FSMContext):
    """Обрабатывает выбор даты окончания."""

    _, _, year, month, day = callback.data.split(":")
    end_date = date(int(year), int(month), int(day))

    data = await state.get_data()
    start_date = date.fromisoformat(data["start_date"])

    if end_date < start_date:
        await callback.answer("❌ Дата окончания не может быть раньше начала!",
                              show_alert=True)
        return

    await state.update_data(end_date=end_date.isoformat())

    type_name = REQUEST_TYPE_LABELS.get(data["request_type"],
                                        data["request_type"])

    await callback.message.edit_text(
        f"📝 <b>Новая заявка</b>\n\n"
        f"Тип: {type_name}\n"
        f"📅 Период: {start_date.strftime('%d.%m.%Y')} — "
        f"{end_date.strftime('%d.%m.%Y')}\n\n"
        f"💬 Введите <b>комментарий</b> (причина отсутствия)\n"
        f"Или отправьте <b>-</b> чтобы пропустить:",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(CreateRequestStates.entering_comment)
    await callback.answer()


@router.callback_query(F.data.startswith("end:ignore"))
async def ignore_end(callback: CallbackQuery):
    """Игнорирует нажатие на неактивную кнопку."""

    await callback.answer()


@router.message(CreateRequestStates.entering_comment)
async def process_comment(message: Message, state: FSMContext):
    """Обрабатывает ввод комментария."""

    comment = message.text.strip()
    if comment == "-":
        comment = None

    await state.update_data(comment=comment)
    data = await state.get_data()

    start_date = date.fromisoformat(data["start_date"])
    end_date = date.fromisoformat(data["end_date"])
    type_name = REQUEST_TYPE_LABELS.get(data["request_type"],
                                        data["request_type"])

    await message.answer(
        f"📋 <b>Проверьте заявку:</b>\n\n"
        f"📌 Тип: {type_name}\n"
        f"📅 Период: {start_date.strftime('%d.%m.%Y')} — "
        f"{end_date.strftime('%d.%m.%Y')}\n"
        f"💬 Комментарий: {comment or 'Не указан'}\n\n"
        f"Всё верно?",
        reply_markup=get_confirm_keyboard()
    )
    await state.set_state(CreateRequestStates.confirming)


@router.callback_query(F.data == "req_edit")
async def edit_request(callback: CallbackQuery, state: FSMContext):
    """Возвращает к началу создания заявки."""

    await state.set_state(CreateRequestStates.choosing_type)
    await callback.message.edit_text(
        "📝 <b>Новая заявка</b>\n\n"
        "Выберите тип отсутствия:",
        reply_markup=get_request_type_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data == "req_confirm")
async def confirm_request(callback: CallbackQuery, state: FSMContext, session):
    """Сохраняет заявку в базу данных."""

    data = await state.get_data()

    result = await session.execute(
        select(Employee).where(Employee.telegram_id == callback.from_user.id)
    )
    employee = result.scalar_one_or_none()

    if not employee:
        await callback.message.edit_text("❌ Ошибка: профиль не найден")
        await state.clear()
        await callback.answer()
        return

    request = AbsenceRequest(
        employee_id=employee.id,
        request_type=data["request_type"],
        start_date=date.fromisoformat(data["start_date"]),
        end_date=date.fromisoformat(data["end_date"]),
        comment=data.get("comment"),
        status=RequestStatusEnum.PENDING.value
    )
    session.add(request)
    await session.flush()

    history = AbsenceRequestHistory(
        request_id=request.id,
        changed_by=employee.id,
        change_type=ChangeTypeEnum.CREATED.value,
        new_value=RequestStatusEnum.PENDING.value,
        reason="Заявка создана"
    )
    session.add(history)
    await session.commit()

    await state.clear()

    type_name = REQUEST_TYPE_LABELS.get(data["request_type"],
                                        data["request_type"])
    start = date.fromisoformat(data["start_date"]).strftime('%d.%m.%Y')
    end = date.fromisoformat(data["end_date"]).strftime('%d.%m.%Y')

    await callback.message.edit_text(
        f"✅ <b>Заявка отправлена!</b>\n\n"
        f"📌 Тип: {type_name}\n"
        f"📅 Период: {start} — {end}\n"
        f"🕐 Статус: ожидает рассмотрения\n\n"
        f"Вы получите уведомление, когда заявку рассмотрят."
    )
    menu = await get_menu_by_role(session, callback.from_user.id)
    await callback.message.answer("Главное меню:", reply_markup=menu)
    await callback.answer("Заявка отправлена!")
