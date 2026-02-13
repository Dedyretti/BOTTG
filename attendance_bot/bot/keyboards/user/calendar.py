from datetime import date
from calendar import monthcalendar

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.lexicon.lexicon import days, months


def get_calendar_keyboard(
    year: int = None,
    month: int = None,
    prefix: str = "cal"
) -> InlineKeyboardMarkup:
    """Создаёт inline-календарь для выбора даты."""

    today = date.today()
    year = year or today.year
    month = month or today.month

    builder = InlineKeyboardBuilder()

    builder.button(
        text="◀️",
        callback_data=f"{prefix}:prev:{year}:{month}"
    )
    builder.button(
        text=f"{months[month]} {year}",
        callback_data=f"{prefix}:ignore"
    )
    builder.button(
        text="▶️",
        callback_data=f"{prefix}:next:{year}:{month}"
    )

    for day in days:
        builder.button(text=day, callback_data=f"{prefix}:ignore")

    for week in monthcalendar(year, month):
        for day_num in week:
            if day_num == 0:
                builder.button(
                    text=" ",
                    callback_data=f"{prefix}:ignore"
                )
            else:
                current_date = date(year, month, day_num)
                if current_date < today:
                    # Прошедшая дата - callback для алерта
                    builder.button(
                        text=f"·{day_num}·",
                        callback_data=f"{prefix}:past:{year}:{month}:{day_num}"
                    )
                else:
                    # Доступная дата
                    builder.button(
                        text=str(day_num),
                        callback_data=f"{prefix}:day:{year}:{month}:{day_num}"
                    )

    builder.button(text="❌ Отмена", callback_data="req_cancel")

    builder.adjust(3, 7, 7, 7, 7, 7, 7, 1)

    return builder.as_markup()


def get_prev_month(year: int, month: int) -> tuple[int, int]:
    """Возвращает предыдущий месяц."""

    if month == 1:
        return year - 1, 12
    return year, month - 1


def get_next_month(year: int, month: int) -> tuple[int, int]:
    """Возвращает следующий месяц."""

    if month == 12:
        return year + 1, 1
    return year, month + 1