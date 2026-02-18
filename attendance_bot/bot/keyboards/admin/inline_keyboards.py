from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def get_confirm_delete_keyboard(employee_id: int):
    """Клавиатура подтверждения удаления."""

    builder = InlineKeyboardBuilder()
    builder.button(
        text="✅ Да, удалить",
        callback_data=f"delete_confirm:{employee_id}"
    )
    builder.button(text="❌ Отмена", callback_data="delete_cancel")
    builder.adjust(2)

    return builder.as_markup()


def get_selection_role_keyboard():
    """Клавиатура выбора роли сотрудника."""

    builder = InlineKeyboardBuilder()
    builder.button(text="👤 Пользователь", callback_data="role:user")
    builder.button(text="👑 Администратор", callback_data="role:admin")
    builder.button(text="❌ Отмена", callback_data="role:cancel")
    builder.adjust(1)

    return builder.as_markup()


def get_confirm_employee_keyboard():
    """Клавиатура подтверждения создания сотрудника."""

    builder = InlineKeyboardBuilder()
    builder.button(
        text="✅ Создать сотрудника",
        callback_data="employee:confirm"
    )
    builder.button(
        text="❌ Отмена",
        callback_data="employee:cancel"
    )
    builder.adjust(1)

    return builder.as_markup()


def get_all_requests_pagination_keyboard(
    page: int,
    total_pages: int
) -> InlineKeyboardMarkup:
    """Создаёт клавиатуру пагинации для всех заявок."""
    builder = InlineKeyboardBuilder()

    nav_buttons = []

    if page > 0:
        nav_buttons.append(InlineKeyboardButton(
            text="◀️ Назад",
            callback_data=f"all_req:page:{page - 1}"
        ))

    nav_buttons.append(InlineKeyboardButton(
        text=f"{page + 1}/{total_pages}",
        callback_data="all_req:ignore"
    ))

    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton(
            text="Вперёд ▶️",
            callback_data=f"all_req:page:{page + 1}"
        ))

    builder.row(*nav_buttons)

    builder.row(InlineKeyboardButton(
        text="✖️ Закрыть",
        callback_data="all_req:close"
    ))

    return builder.as_markup()
