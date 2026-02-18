from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def get_activation_keyboard() -> InlineKeyboardMarkup:
    """Создает inline-клавиатуру с кнопкой активации."""

    builder = InlineKeyboardBuilder()

    builder.add(
        InlineKeyboardButton(
            text="🔑 Активируем",
            callback_data="activate_account"
        )
    )

    return builder.as_markup()
