"""Inline-клавиатуры для создания заявки."""

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.lexicon.lexicon import type_names as REQUEST_TYPE_LABELS


def get_request_type_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора типа отсутствия."""

    builder = InlineKeyboardBuilder()

    for req_type, label in REQUEST_TYPE_LABELS.items():
        builder.button(
            text=label,
            callback_data=f"req_type:{req_type}"
        )

    builder.button(text="❌ Отмена", callback_data="req_cancel")
    builder.adjust(1)

    return builder.as_markup()


def get_confirm_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура подтверждения заявки."""

    builder = InlineKeyboardBuilder()

    builder.button(text="✅ Подтвердить", callback_data="req_confirm")
    builder.button(text="✏️ Изменить", callback_data="req_edit")
    builder.button(text="❌ Отмена", callback_data="req_cancel")
    builder.adjust(2, 1)

    return builder.as_markup()


def get_cancel_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура с кнопкой отмены."""

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="req_cancel")]
        ]
    )
