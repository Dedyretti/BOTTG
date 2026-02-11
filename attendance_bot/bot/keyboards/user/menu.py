from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

user_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📝 Подать заявку")],
        [KeyboardButton(text="📋 Мои заявки")],
    ],
    resize_keyboard=True
)
