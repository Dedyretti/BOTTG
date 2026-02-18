from datetime import datetime

import pytz
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from bot.keyboards.user.calendar import get_calendar_keyboard
from bot.keyboards.user.inline_keyboards import (
    get_back_cancel_keyboard,
    get_comment_keyboard,
    get_time_selection_keyboard,
)
from bot.lexicon.lexicon import (
    REQUEST_TYPE_LABELS,
    RequestMessages,
)
from bot.states.states_fsm import CreateRequestStates
from bot.utils.utils import send_new_message
from database.crud.requests import create_absence_request

router = Router(name="request_partial")

LOCAL_TIMEZONE = pytz.timezone('Europe/Moscow')


async def show_partial_date_selection(
    callback: CallbackQuery,
    state: FSMContext,
    type_name: str,
    builder
):
    """Показывает выбор даты для частичного отсутствия."""
    text = (
        f"{RequestMessages.NEW_REQUEST}\n\n"
        f"Тип: {type_name}\n\n"
        f"{RequestMessages.CHOOSE_PARTIAL_DATE}"
    )

    keyboard = get_calendar_keyboard(
        prefix="partial",
        extra_buttons=builder.as_markup()
    )

    await send_new_message(callback, text, keyboard, state)
    await state.set_state(CreateRequestStates.entering_partial_date)


@router.callback_query(F.data.startswith("partial:day:"))
async def process_partial_date(
    callback: CallbackQuery,
    state: FSMContext
):
    """Обрабатывает выбор даты для частичного отсутствия."""
    _, _, year, month, day = callback.data.split(":")
    year, month, day = int(year), int(month), int(day)

    await state.update_data(
        partial_year=year,
        partial_month=month,
        partial_day=day
    )

    type_name = REQUEST_TYPE_LABELS.get(
        "partial_absence",
        "Частичное отсутствие"
    )

    builder = get_back_cancel_keyboard(
        back_callback="back:to_partial_date"
    )

    text = (
        f"{RequestMessages.NEW_REQUEST}\n\n"
        f"Тип: {type_name}\n"
        f"📅 Дата: <b>{day:02d}.{month:02d}.{year}</b>\n\n"
        f"{RequestMessages.CHOOSE_START_TIME}"
    )

    keyboard = get_time_selection_keyboard(
        prefix="partial_start",
        start_hour=8,
        end_hour=19,
        extra_buttons=builder.as_markup()
    )

    await send_new_message(callback, text, keyboard, state)
    await state.set_state(CreateRequestStates.entering_partial_start_time)
    await callback.answer()


@router.callback_query(F.data.startswith("partial_start:hour:"))
async def process_partial_start_time(
    callback: CallbackQuery,
    state: FSMContext
):
    """Обрабатывает выбор времени начала для частичного отсутствия."""
    _, _, hour = callback.data.split(":")
    hour = int(hour)

    await state.update_data(partial_start_hour=hour)

    data = await state.get_data()
    year = data["partial_year"]
    month = data["partial_month"]
    day = data["partial_day"]

    type_name = REQUEST_TYPE_LABELS.get(
        "partial_absence",
        "Частичное отсутствие"
    )

    builder = get_back_cancel_keyboard(
        back_callback="back:to_partial_start_time"
    )

    text = (
        f"{RequestMessages.NEW_REQUEST}\n\n"
        f"Тип: {type_name}\n"
        f"📅 Дата: <b>{day:02d}.{month:02d}.{year}</b>\n"
        f"⏰ Начало: <b>{hour:02d}:00</b>\n\n"
        f"{RequestMessages.CHOOSE_END_TIME}"
    )

    keyboard = get_time_selection_keyboard(
        prefix="partial_end",
        start_hour=hour + 1,
        end_hour=19,
        extra_buttons=builder.as_markup()
    )

    await send_new_message(callback, text, keyboard, state)
    await state.set_state(CreateRequestStates.entering_partial_end_time)
    await callback.answer()


@router.callback_query(F.data.startswith("partial_end:hour:"))
async def process_partial_end_time(
    callback: CallbackQuery,
    state: FSMContext
):
    """Обрабатывает выбор времени окончания для частичного отсутствия."""
    _, _, hour = callback.data.split(":")
    hour = int(hour)

    data = await state.get_data()
    year = data["partial_year"]
    month = data["partial_month"]
    day = data["partial_day"]
    start_hour = data["partial_start_hour"]

    start_datetime = LOCAL_TIMEZONE.localize(
        datetime(year, month, day, start_hour, 0, 0)
    )
    end_datetime = LOCAL_TIMEZONE.localize(
        datetime(year, month, day, hour, 0, 0)
    )

    if end_datetime <= start_datetime:
        await callback.answer(
            "❌ Время окончания должно быть позже времени начала!",
            show_alert=True
        )
        return

    await state.update_data(
        start_date=start_datetime.isoformat(),
        end_date=end_datetime.isoformat()
    )

    type_name = REQUEST_TYPE_LABELS.get(
        "partial_absence",
        "Частичное отсутствие"
    )

    builder = get_back_cancel_keyboard(
        back_callback="back:to_partial_end_time"
    )

    text = (
        f"{RequestMessages.NEW_REQUEST}\n\n"
        f"Тип: {type_name}\n"
        f"📅 Дата: <b>{day:02d}.{month:02d}.{year}</b>\n"
        f"⏰ Время: <b>{start_hour:02d}:00 — {hour:02d}:00</b>\n\n"
        f"{RequestMessages.ENTER_COMMENT}"
    )

    await send_new_message(
        callback,
        text,
        get_comment_keyboard(extra_buttons=builder.as_markup()),
        state
    )
    await state.set_state(CreateRequestStates.entering_comment)
    await callback.answer()


async def create_partial_request(session, telegram_id: int, data: dict):
    """Создаёт заявку на частичное отсутствие."""
    start_datetime = datetime.fromisoformat(data["start_date"])
    end_datetime = datetime.fromisoformat(data["end_date"])

    return await create_absence_request(
        session=session,
        telegram_id=telegram_id,
        request_type="partial_absence",
        start_date=start_datetime,
        end_date=end_datetime,
        comment=data.get("comment"),
    )
