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


def get_cancel_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура с кнопкой отмены."""

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="req_cancel")]
        ]
    )


def comment_keyboard():

    """Клавиатура для этапа ввода комментария."""

    builder = InlineKeyboardBuilder()
    builder.button(text="⏭ Пропустить", callback_data="comment:skip")
    builder.button(text="❌ Отмена", callback_data="req_cancel")
    builder.adjust(2)

    return builder.as_markup()


def get_user_request_keyboard(
    request_id: int,
    current_index: int,
    total_count: int
) -> InlineKeyboardMarkup:
    """Клавиатура для просмотра заявки пользователем."""

    builder = InlineKeyboardBuilder()

    builder.button(
        text="🚫 Отменить заявку",
        callback_data=f"user_cancel_req:{request_id}"
    )

    if current_index > 0:
        builder.button(
            text="◀️ Пред.",
            callback_data=f"user_req_nav:{current_index - 1}"
        )
    else:
        builder.button(text="◀️", callback_data="user_req_nav:ignore")

    builder.button(
        text=f"{current_index + 1}/{total_count}",
        callback_data="user_req_nav:ignore"
    )

    if current_index < total_count - 1:
        builder.button(
            text="След. ▶️",
            callback_data=f"user_req_nav:{current_index + 1}"
        )
    else:
        builder.button(text="▶️", callback_data="user_req_nav:ignore")

    builder.button(
        text="🔙 Назад в меню",
        callback_data="user_back_menu"
    )

    builder.adjust(1, 3, 1)

    return builder.as_markup()


def get_cancel_confirm_keyboard(
    request_id: int
) -> InlineKeyboardMarkup:
    """Клавиатура подтверждения отмены заявки."""

    builder = InlineKeyboardBuilder()
    builder.button(
        text="✅ Да, отменить",
        callback_data=f"user_confirm_cancel:{request_id}"
    )
    builder.button(
        text="❌ Нет, оставить",
        callback_data="user_cancel_back"
    )
    builder.adjust(2)

    return builder.as_markup()


def get_confirm_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура подтверждения заявки."""

    builder = InlineKeyboardBuilder()

    builder.button(
        text="✅ Подтвердить",
        callback_data="req_confirm"
    )
    builder.button(
        text="✏️ Изменить",
        callback_data="req_edit"
    )
    builder.button(
        text="❌ Отмена",
        callback_data="req_cancel"
    )
    builder.adjust(2, 1)

    return builder.as_markup()
