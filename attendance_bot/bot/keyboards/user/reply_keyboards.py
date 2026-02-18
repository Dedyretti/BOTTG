from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
)

from bot.lexicon.lexicon import MenuButtons


def get_user_menu() -> ReplyKeyboardMarkup:
    """Создаёт reply-клавиатуру главного меню пользователя."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text=MenuButtons.SUBMIT_REQUEST),
                KeyboardButton(text=MenuButtons.MY_REQUESTS),
            ],
        ],
        resize_keyboard=True,
        one_time_keyboard=False,
    )


user_menu = get_user_menu()
