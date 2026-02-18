from datetime import date
from calendar import monthcalendar

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.lexicon.lexicon import days, months


def get_calendar_keyboard(
    year: int = None,
    month: int = None,
    prefix: str = "cal",
    extra_buttons: InlineKeyboardMarkup = None
) -> InlineKeyboardMarkup:
    """Создаёт inline-календарь для выбора даты."""

    today = date.today()
    year = year or today.year
    month = month or today.month

    if isinstance(month, str):
        month = int(month)
    if isinstance(year, str):
        year = int(year)

    builder = InlineKeyboardBuilder()

    row = [
        InlineKeyboardButton(
            text="◀️",
            callback_data=f"{prefix}:prev:{year}:{month}"
        ),
        InlineKeyboardButton(
            text=f"{months[month]} {year}",
            callback_data=f"{prefix}:ignore"
        ),
        InlineKeyboardButton(
            text="▶️",
            callback_data=f"{prefix}:next:{year}:{month}"
        )
    ]
    builder.row(*row)

    week_days = [
        InlineKeyboardButton(
            text=day,
            callback_data=f"{prefix}:ignore"
        )
        for day in days
    ]
    builder.row(*week_days)

    calendar_weeks = monthcalendar(year, month)
    for week in calendar_weeks:
        row_buttons = []
        for day_num in week:
            if day_num == 0:
                row_buttons.append(
                    InlineKeyboardButton(
                        text=" ",
                        callback_data=f"{prefix}:ignore"
                    )
                )
            else:
                current_date = date(year, month, day_num)
                if current_date < today:
                    row_buttons.append(
                        InlineKeyboardButton(
                            text=f"·{day_num}·",
                            callback_data=(
                                f"{prefix}:past:{year}:{month}:{day_num}"
                            )
                        )
                    )
                else:
                    row_buttons.append(
                        InlineKeyboardButton(
                            text=str(day_num),
                            callback_data=(
                                f"{prefix}:day:{year}:{month}:{day_num}"
                            )
                        )
                    )
        builder.row(*row_buttons)
    if extra_buttons:
        calendar_builder = InlineKeyboardBuilder.from_markup(
            builder.as_markup())
        calendar_builder.attach(InlineKeyboardBuilder.from_markup(
            extra_buttons))
        return calendar_builder.as_markup()

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
