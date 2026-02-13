from datetime import date

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.keyboards.admin.menu import admin_menu
from bot.keyboards.user.calendar import (
    get_calendar_keyboard,
    get_next_month,
    get_prev_month,
)
from bot.keyboards.user.request import comment_keyboard
from bot.keyboards.user.menu import user_menu
from bot.keyboards.user.request import (
    REQUEST_TYPE_LABELS,
    get_confirm_keyboard,
    get_request_type_keyboard,
)
from bot.services.notifications import NotificationService
from bot.states.states_fsm import CreateRequestStates
from database.crud.employee import (
    get_employee_by_telegram_id,
    get_employee_role
)
from database.crud.requests import create_absence_request

router = Router()


def _get_menu_by_role(role: str | None):
    """Возвращает клавиатуру меню по роли."""

    if role in ("admin", "superuser"):
        return admin_menu
    return user_menu


@router.message(F.text == "📝 Подать заявку")
async def start_request(message: Message, state: FSMContext):
    """Начинает процесс создания заявки."""

    await state.clear()
    await state.set_state(CreateRequestStates.choosing_type)
    await message.answer(
        "📝 <b>Новая заявка</b>\n\nВыберите тип отсутствия:",
        reply_markup=get_request_type_keyboard()
    )


@router.callback_query(F.data == "req_cancel")
async def cancel_request(callback: CallbackQuery, state: FSMContext, session):
    """Отменяет создание заявки."""

    await state.clear()
    await callback.message.edit_text("❌ Создание заявки отменено")

    role = await get_employee_role(session, callback.from_user.id)
    await callback.message.answer(
        "Главное меню:",
        reply_markup=_get_menu_by_role(role)
    )
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


@router.callback_query(F.data.startswith("start:past:"))
async def past_date_start_alert(callback: CallbackQuery):
    """Алерт при попытке выбрать прошедшую дату начала."""

    await callback.answer(
        "❌ Нельзя выбрать дату в прошлом!\n"
        "Выберите сегодняшний или будущий день.",
        show_alert=True
    )


@router.callback_query(F.data.startswith("end:past:"))
async def past_date_end_alert(callback: CallbackQuery):
    """Алерт при попытке выбрать прошедшую дату окончания."""

    await callback.answer(
        "❌ Нельзя выбрать дату в прошлом!\n"
        "Выберите сегодняшний или будущий день.",
        show_alert=True
    )


@router.callback_query(F.data.startswith("start:ignore"))
async def ignore_start_button(callback: CallbackQuery):
    """Игнорировать нажатие на неактивную кнопку."""

    await callback.answer()


@router.callback_query(F.data.startswith("end:ignore"))
async def ignore_end_button(callback: CallbackQuery):
    """Игнорировать нажатие на неактивную кнопку."""

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
    type_name = REQUEST_TYPE_LABELS.get(
        data["request_type"],
        data["request_type"]
    )

    await callback.message.edit_text(
        f"📝 <b>Новая заявка</b>\n\n"
        f"Тип: {type_name}\n"
        f"📅 Начало: <b>{start_date.strftime('%d.%m.%Y')}</b>\n\n"
        f"📅 Выберите <b>дату окончания</b>:",
        reply_markup=get_calendar_keyboard(int(year), int(month), prefix="end")
    )
    await state.set_state(CreateRequestStates.entering_end_date)
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

    if "start_date" not in data:
        await callback.answer(
            "❌ Сначала выберите дату начала",
            show_alert=True
        )
        return

    start_date = date.fromisoformat(data["start_date"])

    if end_date < start_date:
        await callback.answer(
            "❌ Дата окончания не может быть раньше начала!",
            show_alert=True
        )
        return

    await state.update_data(end_date=end_date.isoformat())

    type_name = REQUEST_TYPE_LABELS.get(
        data["request_type"],
        data["request_type"]
    )

    await callback.message.edit_text(
        f"📝 <b>Новая заявка</b>\n\n"
        f"Тип: {type_name}\n"
        f"📅 Период: {start_date.strftime('%d.%m.%Y')} — "
        f"{end_date.strftime('%d.%m.%Y')}\n\n"
        f"💬 Введите комментарий (причина):",
        reply_markup=comment_keyboard()
    )
    await state.set_state(CreateRequestStates.entering_comment)
    await callback.answer()


@router.callback_query(F.data == "comment:skip")
async def skip_comment(callback: CallbackQuery, state: FSMContext, session):
    """Пропускает ввод комментария."""

    data = await state.get_data()

    if "start_date" not in data or "end_date" not in data:
        await callback.answer(
            "❌ Данные устарели. Начните заново.",
            show_alert=True
        )
        await state.clear()

        role = await get_employee_role(session, callback.from_user.id)
        await callback.message.edit_text("❌ Сессия истекла")
        await callback.message.answer(
            "Главное меню:",
            reply_markup=_get_menu_by_role(role)
        )
        return

    await state.update_data(comment=None)

    start_date = date.fromisoformat(data["start_date"])
    end_date = date.fromisoformat(data["end_date"])
    type_name = REQUEST_TYPE_LABELS.get(
        data["request_type"],
        data["request_type"]
    )

    await callback.message.edit_text(
        f"📋 <b>Проверьте заявку:</b>\n\n"
        f"📌 Тип: {type_name}\n"
        f"📅 Период: {start_date.strftime('%d.%m.%Y')} — "
        f"{end_date.strftime('%d.%m.%Y')}\n"
        f"💬 Комментарий: Не указан\n\n"
        f"Всё верно?",
        reply_markup=get_confirm_keyboard()
    )
    await state.set_state(CreateRequestStates.confirming)
    await callback.answer()


@router.message(CreateRequestStates.entering_comment)
async def process_comment(message: Message, state: FSMContext):
    """Обрабатывает ввод комментария текстом."""

    comment = message.text.strip()
    if comment == "-":
        comment = None

    await state.update_data(comment=comment)
    data = await state.get_data()

    start_date = date.fromisoformat(data["start_date"])
    end_date = date.fromisoformat(data["end_date"])
    type_name = REQUEST_TYPE_LABELS.get(
        data["request_type"],
        data["request_type"]
    )

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

    await state.clear()
    await state.set_state(CreateRequestStates.choosing_type)
    await callback.message.edit_text(
        "📝 <b>Новая заявка</b>\n\nВыберите тип отсутствия:",
        reply_markup=get_request_type_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data == "req_confirm")
async def confirm_request(
    callback: CallbackQuery,
    state: FSMContext,
    session,
    bot: Bot
):
    """Сохраняет заявку и отправляет уведомления."""

    data = await state.get_data()

    if "start_date" not in data or "end_date" not in data:
        await callback.answer(
            "❌ Данные устарели. Начните заново.",
            show_alert=True
        )
        await state.clear()
        return

    start_date = date.fromisoformat(data["start_date"])
    end_date = date.fromisoformat(data["end_date"])

    request = await create_absence_request(
        session=session,
        telegram_id=callback.from_user.id,
        request_type=data["request_type"],
        start_date=start_date,
        end_date=end_date,
        comment=data.get("comment"),
    )

    if not request:
        await callback.message.edit_text("❌ Ошибка: профиль не найден")
        await state.clear()
        await callback.answer()
        return

    employee = await get_employee_by_telegram_id(
        session, callback.from_user.id
    )

    notifier = NotificationService(bot)

    admin_results = await notifier.notify_admins_new_request(
        session, request, employee
    )

    await notifier.notify_user_request_created(
        callback.from_user.id, request
    )

    await state.clear()

    type_name = REQUEST_TYPE_LABELS.get(
        data["request_type"],
        data["request_type"]
    )

    await callback.message.edit_text(
        f"✅ <b>Заявка #{request.id} отправлена!</b>\n\n"
        f"📌 Тип: {type_name}\n"
        f"📅 Период: {start_date.strftime('%d.%m.%Y')} — "
        f"{end_date.strftime('%d.%m.%Y')}\n\n"
        f"📨 Уведомлено администраторов: {len(admin_results['success'])}"
    )

    role = await get_employee_role(session, callback.from_user.id)
    await callback.message.answer(
        "Главное меню:",
        reply_markup=_get_menu_by_role(role)
    )
    await callback.answer("✅ Заявка отправлена!")
