from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

user_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Мой профиль")],
        [KeyboardButton(text="Помощь")]
    ],
    resize_keyboard=True
)
