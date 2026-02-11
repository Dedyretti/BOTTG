from aiogram.types import ReplyKeyboardMarkup, KeyboardButton


admin_menu = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="📋 Новые заявки"),
            KeyboardButton(text="📁 Все заявки")
        ],
        [
            KeyboardButton(text="👥 Сотрудники"),
            KeyboardButton(text="📝 Подать заявку"),
        ],
        [
            KeyboardButton(text="📊 Отчёты"),
            KeyboardButton(text="📋 Мои заявки")
        ],
    ],
    resize_keyboard=True,
    input_field_placeholder="Выберите действие"
)


admin_cancel_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="❌ Отмена")]
    ],
    resize_keyboard=True
)


def get_employees_menu():
    """Возвращает клавиатуру для управления сотрудниками."""

    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="📋 Список сотрудников"),
                KeyboardButton(text="➕ Добавить сотрудника")
            ],
            [
                KeyboardButton(text="🔑 Создать инвайт-код"),
                KeyboardButton(text="🗑 Удалить сотрудника")
            ],
            [
                KeyboardButton(text="🔙 Главное меню")
            ],
        ],
        resize_keyboard=True
    )


def selektion_role_menu():
    """Клавиатура выбора роли при добавлении сотрудника."""

    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="Пользователь"),
                KeyboardButton(text="Администратор")
            ],
            [
                KeyboardButton(text="🔙 Главное меню")
            ],
        ],
        resize_keyboard=True
    )
