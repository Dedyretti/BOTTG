from datetime import date as date_cls, datetime

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from bot.keyboards.user.calendar import get_calendar_keyboard
from bot.keyboards.user.inline_keyboards import (
    get_cancel_keyboard,
    get_back_cancel_keyboard,
    get_comment_keyboard,
    get_edit_keyboard_by_type,
    get_request_type_keyboard,
    get_time_selection_keyboard,
)
from bot.lexicon.lexicon import (
    REQUEST_TYPE_LABELS,
    CallbackData,
    RequestMessages,
)
from bot.states.states_fsm import CreateRequestStates
from bot.utils.utils import (
    format_request_preview,
    send_new_message,
    safe_delete_message,
)

router = Router(name="request_navigation")


def _get_partial_date(data: dict) -> date_cls:
    """Собирает дату из partial_year/month/day."""
    return date_cls(
        data["partial_year"],
        data["partial_month"],
        data["partial_day"]
    )


def _get_partial_times(data: dict) -> tuple[str, str]:
    """Получает время начала и окончания из state."""
    start_hour = data["partial_start_hour"]
    start_time = f"{start_hour:02d}:00"

    end_dt = datetime.fromisoformat(data["end_date"])
    end_time = end_dt.strftime('%H:%M')

    return start_time, end_time


async def show_request_preview(
    callback: CallbackQuery,
    state: FSMContext
):
    """Показывает предпросмотр заявки с вариантами редактирования."""
    data = await state.get_data()
    await state.set_state(CreateRequestStates.confirming)
    await state.update_data(keyboard_type="preview")

    await send_new_message(
        callback,
        format_request_preview(data),
        get_edit_keyboard_by_type(data["request_type"]),
        state
    )


@router.callback_query(F.data.startswith("edit:"))
async def edit_request_item(
    callback: CallbackQuery,
    state: FSMContext
):
    """Редактирует конкретный пункт заявки."""
    item = callback.data.split(":")[1]
    data = await state.get_data()
    request_type = data["request_type"]

    if item == "type":
        await edit_type(callback, state)

    elif item == "partial_date" and request_type == "partial_absence":
        await edit_partial_date(callback, state)

    elif item == "partial_time" and request_type == "partial_absence":
        await edit_partial_time(callback, state, data)

    elif item == "start_date" and request_type != "partial_absence":
        await edit_start_date(callback, state)

    elif item == "end_date" and request_type != "partial_absence":
        await edit_end_date(callback, state, data)

    elif item == "comment":
        await edit_comment(callback, state, data)


async def edit_type(callback: CallbackQuery, state: FSMContext):
    """Редактирование типа заявки."""
    await state.set_state(CreateRequestStates.choosing_type)
    await state.update_data(keyboard_type="type_edit")

    builder = get_back_cancel_keyboard(
        back_callback=CallbackData.BACK_TO_PREVIEW
    )

    text = (
        f"{RequestMessages.EDIT_REQUEST}\n\n"
        f"{RequestMessages.CHOOSE_TYPE}"
    )
    keyboard = get_request_type_keyboard(
        extra_buttons=builder.as_markup()
    )

    await send_new_message(callback, text, keyboard, state)


async def edit_partial_date(
    callback: CallbackQuery,
    state: FSMContext
):
    """Редактирование даты частичного отсутствия."""
    await state.set_state(CreateRequestStates.entering_partial_date)
    await state.update_data(keyboard_type="partial_date_edit")

    builder = get_back_cancel_keyboard(
        back_callback=CallbackData.BACK_TO_PREVIEW
    )

    text = (
        f"{RequestMessages.EDIT_REQUEST}\n\n"
        f"{RequestMessages.CHOOSE_PARTIAL_DATE}"
    )
    keyboard = get_calendar_keyboard(
        prefix="partial",
        extra_buttons=builder.as_markup()
    )

    await send_new_message(callback, text, keyboard, state)


async def edit_partial_time(
    callback: CallbackQuery,
    state: FSMContext,
    data: dict
):
    """Редактирование времени частичного отсутствия."""
    await state.set_state(CreateRequestStates.entering_partial_start_time)
    await state.update_data(keyboard_type="partial_time_edit")

    date_obj = _get_partial_date(data)
    type_name = REQUEST_TYPE_LABELS.get(
        data["request_type"],
        data["request_type"]
    )

    builder = get_back_cancel_keyboard(
        back_callback=CallbackData.BACK_TO_PREVIEW
    )

    text = (
        f"{RequestMessages.EDIT_REQUEST}\n\n"
        f"Тип: {type_name}\n"
        f"📅 Дата: <b>{date_obj.strftime('%d.%m.%Y')}</b>\n\n"
        f"{RequestMessages.CHOOSE_START_TIME}"
    )
    keyboard = get_time_selection_keyboard(
        prefix="partial_start",
        start_hour=8,
        end_hour=19,
        extra_buttons=builder.as_markup()
    )

    await send_new_message(callback, text, keyboard, state)


async def edit_start_date(
    callback: CallbackQuery,
    state: FSMContext
):
    """Редактирование даты начала."""
    await state.set_state(CreateRequestStates.entering_start_date)
    await state.update_data(keyboard_type="start_date_edit")

    builder = get_back_cancel_keyboard(
        back_callback=CallbackData.BACK_TO_PREVIEW
    )

    text = (
        f"{RequestMessages.EDIT_REQUEST}\n\n"
        f"{RequestMessages.CHOOSE_START_DATE}"
    )
    keyboard = get_calendar_keyboard(
        prefix="start",
        extra_buttons=builder.as_markup()
    )

    await send_new_message(callback, text, keyboard, state)


async def edit_end_date(
    callback: CallbackQuery,
    state: FSMContext,
    data: dict
):
    """Редактирование даты окончания."""
    await state.set_state(CreateRequestStates.entering_end_date)
    await state.update_data(keyboard_type="end_date_edit")

    start_dt = datetime.fromisoformat(data["start_date"])

    builder = get_back_cancel_keyboard(
        back_callback=CallbackData.BACK_TO_PREVIEW
    )

    text = (
        f"{RequestMessages.EDIT_REQUEST}\n\n"
        f"{RequestMessages.CHOOSE_END_DATE}"
    )
    keyboard = get_calendar_keyboard(
        start_dt.year,
        start_dt.month,
        prefix="end",
        extra_buttons=builder.as_markup()
    )

    await send_new_message(callback, text, keyboard, state)


async def edit_comment(
    callback: CallbackQuery,
    state: FSMContext,
    data: dict
):
    """Редактирование комментария."""
    await state.set_state(CreateRequestStates.entering_comment)
    await state.update_data(keyboard_type="comment_edit")

    request_type = data["request_type"]
    type_name = REQUEST_TYPE_LABELS.get(request_type, request_type)

    builder = get_back_cancel_keyboard(
        back_callback=CallbackData.BACK_TO_PREVIEW
    )

    if request_type == "partial_absence":
        date_obj = _get_partial_date(data)
        start_time, end_time = _get_partial_times(data)

        text = (
            f"{RequestMessages.EDIT_REQUEST}\n\n"
            f"Тип: {type_name}\n"
            f"📅 Дата: <b>{date_obj.strftime('%d.%m.%Y')}</b>\n"
            f"⏰ Время: <b>{start_time} — {end_time}</b>\n\n"
            f"{RequestMessages.ENTER_NEW_COMMENT}"
        )
    else:
        start_dt = datetime.fromisoformat(data["start_date"])
        end_dt = datetime.fromisoformat(data["end_date"])

        text = (
            f"{RequestMessages.EDIT_REQUEST}\n\n"
            f"Тип: {type_name}\n"
            f"📅 Период: {start_dt.strftime('%d.%m.%Y')} — "
            f"{end_dt.strftime('%d.%m.%Y')}\n\n"
            f"{RequestMessages.ENTER_NEW_COMMENT}"
        )

    await send_new_message(
        callback,
        text,
        get_comment_keyboard(extra_buttons=builder.as_markup()),
        state
    )


@router.callback_query(F.data.startswith("back:"))
async def go_back(callback: CallbackQuery, state: FSMContext):
    """Возвращает на предыдущий шаг."""
    action = callback.data.split(":")[1]
    data = await state.get_data()
    request_type = data.get("request_type")

    if action == "to_type":
        await back_to_type(callback, state)

    elif action == "to_partial_date":
        await back_to_partial_date(callback, state, request_type)

    elif action == "to_partial_start_time":
        await back_to_partial_start_time(callback, state, data)

    elif action == "to_start_date":
        await back_to_start_date(callback, state, request_type)

    elif action == "to_end_date":
        await back_to_end_date(callback, state, data)

    elif action == "to_preview":
        await show_request_preview(callback, state)

    await callback.answer()


async def back_to_type(callback: CallbackQuery, state: FSMContext):
    """Возврат к выбору типа."""
    await state.set_state(CreateRequestStates.choosing_type)
    await state.update_data(keyboard_type="type_selection")

    builder = get_cancel_keyboard()

    text = (
        f"{RequestMessages.NEW_REQUEST}\n\n"
        f"{RequestMessages.CHOOSE_TYPE}"
    )
    keyboard = get_request_type_keyboard(
        extra_buttons=builder.as_markup()
    )

    await send_new_message(callback, text, keyboard, state)


async def back_to_partial_date(
    callback: CallbackQuery,
    state: FSMContext,
    request_type: str
):
    """Возврат к выбору даты частичного отсутствия."""
    await state.set_state(CreateRequestStates.entering_partial_date)
    await state.update_data(keyboard_type="partial_date")

    type_name = REQUEST_TYPE_LABELS.get(request_type, request_type)

    builder = get_back_cancel_keyboard()

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


async def back_to_partial_start_time(
    callback: CallbackQuery,
    state: FSMContext,
    data: dict
):
    """Возврат к выбору времени начала."""
    await state.set_state(CreateRequestStates.entering_partial_start_time)
    await state.update_data(keyboard_type="partial_start_time")

    request_type = data.get("request_type")
    date_obj = _get_partial_date(data)
    type_name = REQUEST_TYPE_LABELS.get(request_type, request_type)

    builder = get_back_cancel_keyboard(
        back_callback="back:to_partial_date"
    )

    text = (
        f"{RequestMessages.NEW_REQUEST}\n\n"
        f"Тип: {type_name}\n"
        f"📅 Дата: <b>{date_obj.strftime('%d.%m.%Y')}</b>\n\n"
        f"{RequestMessages.CHOOSE_START_TIME}"
    )
    keyboard = get_time_selection_keyboard(
        prefix="partial_start",
        start_hour=8,
        end_hour=19,
        extra_buttons=builder.as_markup()
    )

    await send_new_message(callback, text, keyboard, state)


async def back_to_start_date(
    callback: CallbackQuery,
    state: FSMContext,
    request_type: str
):
    """Возврат к выбору даты начала."""
    await state.set_state(CreateRequestStates.entering_start_date)
    await state.update_data(keyboard_type="start_date")

    type_name = REQUEST_TYPE_LABELS.get(request_type, request_type)

    builder = get_back_cancel_keyboard()

    text = (
        f"{RequestMessages.NEW_REQUEST}\n\n"
        f"Тип: {type_name}\n\n"
        f"{RequestMessages.CHOOSE_START_DATE}"
    )
    keyboard = get_calendar_keyboard(
        prefix="start",
        extra_buttons=builder.as_markup()
    )

    await send_new_message(callback, text, keyboard, state)


async def back_to_end_date(
    callback: CallbackQuery,
    state: FSMContext,
    data: dict
):
    """Возврат к выбору даты окончания."""
    await state.set_state(CreateRequestStates.entering_end_date)
    await state.update_data(keyboard_type="end_date")

    request_type = data.get("request_type")
    type_name = REQUEST_TYPE_LABELS.get(request_type, request_type)
    start_dt = datetime.fromisoformat(data["start_date"])

    builder = get_back_cancel_keyboard(
        back_callback="back:to_start_date"
    )

    text = (
        f"{RequestMessages.NEW_REQUEST}\n\n"
        f"Тип: {type_name}\n"
        f"📅 Начало: <b>{start_dt.strftime('%d.%m.%Y')}</b>\n\n"
        f"{RequestMessages.CHOOSE_END_DATE}"
    )
    keyboard = get_calendar_keyboard(
        start_dt.year,
        start_dt.month,
        prefix="end",
        extra_buttons=builder.as_markup()
    )

    await send_new_message(callback, text, keyboard, state)


@router.callback_query(F.data == CallbackData.EDIT)
async def edit_request(callback: CallbackQuery, state: FSMContext):
    """Возвращает к началу создания заявки."""
    await safe_delete_message(callback, state)
    await state.clear()
    await state.set_state(CreateRequestStates.choosing_type)
    await state.update_data(keyboard_type="type_selection")

    builder = get_cancel_keyboard()

    text = (
        f"{RequestMessages.NEW_REQUEST}\n\n"
        f"{RequestMessages.CHOOSE_TYPE}"
    )
    keyboard = get_request_type_keyboard(
        extra_buttons=builder.as_markup()
    )

    await send_new_message(callback, text, keyboard, state)
    await callback.answer()
