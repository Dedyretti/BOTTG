from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def get_request_actions_keyboard(request_id: int) -> InlineKeyboardMarkup:
    """Клавиатура действий с заявкой."""

    builder = InlineKeyboardBuilder()
    builder.button(
        text="✅ Одобрить", callback_data=f"req_approve:{request_id}")
    builder.button(
        text="❌ Отклонить", callback_data=f"req_reject:{request_id}")
    builder.adjust(2)

    return builder.as_markup()


def get_request_view_keyboard(
    request_id: int,
    current_index: int,
    total_count: int
) -> InlineKeyboardMarkup:
    """Клавиатура просмотра заявки с пагинацией."""

    builder = InlineKeyboardBuilder()

    builder.button(
        text="✅ Одобрить", callback_data=f"req_approve:{request_id}")
    builder.button(
        text="❌ Отклонить", callback_data=f"req_reject:{request_id}")

    if current_index > 0:
        builder.button(
            text="◀️ Пред.",
            callback_data=f"req_nav:{current_index - 1}"
        )
    else:
        builder.button(text="◀️", callback_data="req_nav:ignore")

    builder.button(
        text=f"{current_index + 1}/{total_count}",
        callback_data="req_nav:ignore"
    )

    if current_index < total_count - 1:
        builder.button(
            text="След. ▶️",
            callback_data=f"req_nav:{current_index + 1}"
        )
    else:
        builder.button(text="▶️", callback_data="req_nav:ignore")

    builder.button(text="🔙 Назад", callback_data="req_back_to_menu")

    builder.adjust(2, 3, 1)

    return builder.as_markup()


def get_reject_confirm_keyboard(request_id: int) -> InlineKeyboardMarkup:
    """Клавиатура подтверждения отклонения."""

    builder = InlineKeyboardBuilder()
    builder.button(
        text="⏭ Без причины",
        callback_data=f"req_reject_confirm:{request_id}:"
    )
    builder.button(text="❌ Отмена", callback_data="req_reject_cancel")
    builder.adjust(1)

    return builder.as_markup()
