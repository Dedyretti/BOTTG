from aiogram.utils.keyboard import InlineKeyboardBuilder


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
        text="✏️ Изменить",
        callback_data="employee:edit"
    )
    builder.button(
        text="❌ Отмена",
        callback_data="employee:cancel"
    )
    builder.adjust(1)

    return builder.as_markup()
