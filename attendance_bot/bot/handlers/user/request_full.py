import pytz

from datetime import datetime

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from bot.keyboards.user.calendar import get_calendar_keyboard
from bot.keyboards.user.inline_keyboards import (
    get_back_cancel_keyboard,
    get_comment_keyboard,
)
from bot.lexicon.lexicon import (
    REQUEST_TYPE_LABELS,
    RequestMessages,
)
from bot.states.states_fsm import CreateRequestStates
from bot.utils.utils import send_new_message
from database.crud.requests import create_absence_request

router = Router(name="request_full")

LOCAL_TIMEZONE = pytz.timezone('Europe/Moscow')


async def show_start_date_selection(
    callback: CallbackQuery,
    state: FSMContext,
    type_name: str,
    builder
):
    """Показывает выбор даты начала."""
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
    await state.set_state(CreateRequestStates.entering_start_date)


@router.callback_query(F.data.startswith("start:day:"))
async def process_start_date(
    callback: CallbackQuery,
    state: FSMContext
):
    """Обрабатывает выбор даты начала."""
    parts = callback.data.split(":")
    year = int(parts[2])
    month = int(parts[3])
    day = int(parts[4])

    start_datetime = LOCAL_TIMEZONE.localize(
        datetime(year, month, day, 0, 0, 0)
    )

    await state.update_data(start_date=start_datetime.isoformat())

    data = await state.get_data()
    type_name = REQUEST_TYPE_LABELS.get(
        data["request_type"],
        data["request_type"]
    )

    builder = get_back_cancel_keyboard(back_callback="back:to_start_date")

    await callback.message.edit_text(
        f"📝 <b>Новая заявка</b>\n\n"
        f"Тип: {type_name}\n"
        f"📅 Начало: <b>{start_datetime.strftime('%d.%m.%Y')}</b>\n\n"
        f"📅 Выберите <b>дату окончания</b>:",
        reply_markup=get_calendar_keyboard(
            year,
            month,
            prefix="end",
            extra_buttons=builder.as_markup()
        )
    )
    await state.set_state(CreateRequestStates.entering_end_date)
    await callback.answer()


@router.callback_query(F.data.startswith("end:day:"))
async def process_end_date(
    callback: CallbackQuery,
    state: FSMContext
):
    """Обрабатывает выбор даты окончания."""
    parts = callback.data.split(":")
    year = int(parts[2])
    month = int(parts[3])
    day = int(parts[4])

    data = await state.get_data()

    if "start_date" not in data:
        await callback.answer(
            RequestMessages.ERROR_START_DATE_MISSING,
            show_alert=True
        )
        return

    start_date = datetime.fromisoformat(data["start_date"])

    end_datetime = LOCAL_TIMEZONE.localize(
        datetime(year, month, day, 23, 59, 59)
    )

    if end_datetime < start_date:
        await callback.answer(
            RequestMessages.ERROR_END_DATE_BEFORE_START,
            show_alert=True
        )
        return

    await state.update_data(end_date=end_datetime.isoformat())

    type_name = REQUEST_TYPE_LABELS.get(
        data["request_type"],
        data["request_type"]
    )

    builder = get_back_cancel_keyboard(back_callback="back:to_end_date")

    await callback.message.edit_text(
        f"📝 <b>Новая заявка</b>\n\n"
        f"Тип: {type_name}\n"
        f"📅 Период: {start_date.strftime('%d.%m.%Y')} — "
        f"{end_datetime.strftime('%d.%m.%Y')}\n\n"
        f"💬 Введите комментарий (причина):",
        reply_markup=get_comment_keyboard(
            extra_buttons=builder.as_markup()
        )
    )
    await state.set_state(CreateRequestStates.entering_comment)
    await callback.answer()


async def create_full_request(session, telegram_id: int, data: dict):
    """Создаёт заявку на полный день."""
    start_date = datetime.fromisoformat(data["start_date"])
    end_date = datetime.fromisoformat(data["end_date"])

    return await create_absence_request(
        session=session,
        telegram_id=telegram_id,
        request_type=data["request_type"],
        start_date=start_date,
        end_date=end_date,
        comment=data.get("comment"),
    )
