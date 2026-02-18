from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.lexicon.lexicon import ButtonText, CallbackData, REQUEST_TYPE_LABELS


def get_user_request_keyboard(
    request_id: int,
    index: int,
    total: int,
    can_cancel: bool = False
) -> InlineKeyboardMarkup:
    """Создаёт клавиатуру просмотра заявки пользователем."""
    builder = InlineKeyboardBuilder()

    nav_buttons = []

    if index > 0:
        nav_buttons.append(InlineKeyboardButton(
            text="◀️",
            callback_data=f"my_req:page:{index - 1}"
        ))

    nav_buttons.append(InlineKeyboardButton(
        text=f"{index + 1}/{total}",
        callback_data="my_req:ignore"
    ))

    if index < total - 1:
        nav_buttons.append(InlineKeyboardButton(
            text="▶️",
            callback_data=f"my_req:page:{index + 1}"
        ))

    builder.row(*nav_buttons)

    if can_cancel:
        builder.row(InlineKeyboardButton(
            text="🚫 Отменить заявку",
            callback_data=f"my_req:cancel:{request_id}"
        ))

    builder.row(InlineKeyboardButton(
        text="❌ Отмена",
        callback_data="my_req:close"
    ))

    return builder.as_markup()


def get_cancel_confirm_keyboard(
    request_id: int
) -> InlineKeyboardMarkup:
    """Создаёт клавиатуру подтверждения отмены заявки."""
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text="✅ Да, отменить",
            callback_data=f"my_req:cancel_confirm:{request_id}"
        ),
        InlineKeyboardButton(
            text="❌ Нет",
            callback_data="my_req:cancel_back"
        )
    )

    return builder.as_markup()


def get_cancel_keyboard() -> InlineKeyboardBuilder:
    """Создаёт клавиатуру с кнопкой отмены."""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(
        text=ButtonText.CANCEL,
        callback_data=CallbackData.CANCEL
    ))
    return builder


def get_back_cancel_keyboard(
    back_callback: str = CallbackData.BACK_TO_TYPE
) -> InlineKeyboardBuilder:
    """Создаёт клавиатуру с кнопками назад и отмена."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text=ButtonText.BACK,
            callback_data=back_callback
        ),
        InlineKeyboardButton(
            text=ButtonText.CANCEL,
            callback_data=CallbackData.CANCEL
        ),
    )
    return builder


def get_edit_keyboard_by_type(request_type: str) -> InlineKeyboardMarkup:
    """Возвращает клавиатуру редактирования в зависимости от типа."""
    builder = InlineKeyboardBuilder()

    if request_type == "partial_absence":
        builder.row(
            InlineKeyboardButton(
                text=ButtonText.EDIT_TYPE,
                callback_data=CallbackData.EDIT_TYPE
            ),
            InlineKeyboardButton(
                text=ButtonText.EDIT_PARTIAL_DATE,
                callback_data=CallbackData.EDIT_PARTIAL_DATE
            ),
        )
        builder.row(
            InlineKeyboardButton(
                text=ButtonText.EDIT_PARTIAL_TIME,
                callback_data=CallbackData.EDIT_PARTIAL_TIME
            ),
            InlineKeyboardButton(
                text=ButtonText.EDIT_COMMENT,
                callback_data=CallbackData.EDIT_COMMENT
            ),
        )
    else:
        builder.row(
            InlineKeyboardButton(
                text=ButtonText.EDIT_TYPE,
                callback_data=CallbackData.EDIT_TYPE
            ),
            InlineKeyboardButton(
                text=ButtonText.EDIT_START_DATE,
                callback_data=CallbackData.EDIT_START_DATE
            ),
        )
        builder.row(
            InlineKeyboardButton(
                text=ButtonText.CANCEL,
                callback_data=CallbackData.CANCEL
            ),
            InlineKeyboardButton(
                text=ButtonText.EDIT_COMMENT,
                callback_data=CallbackData.EDIT_COMMENT
            ),
        )

    builder.row(
        InlineKeyboardButton(
            text=ButtonText.CONFIRM,
            callback_data=CallbackData.CONFIRM
        ),
    )

    return builder.as_markup()


def get_request_type_keyboard(
    extra_buttons: InlineKeyboardMarkup | None = None
) -> InlineKeyboardMarkup:
    """Создаёт клавиатуру выбора типа заявки."""
    builder = InlineKeyboardBuilder()

    for req_type, label in REQUEST_TYPE_LABELS.items():
        builder.row(InlineKeyboardButton(
            text=label,
            callback_data=f"{CallbackData.REQ_TYPE_PREFIX}{req_type}"
        ))

    if extra_buttons:
        for row in extra_buttons.inline_keyboard:
            builder.row(*row)

    return builder.as_markup()


def get_comment_keyboard(
    extra_buttons: InlineKeyboardMarkup | None = None,
) -> InlineKeyboardMarkup:
    """Создаёт клавиатуру для шага комментария."""
    builder = InlineKeyboardBuilder()

    builder.row(InlineKeyboardButton(
        text=ButtonText.SKIP_COMMENT,
        callback_data=CallbackData.COMMENT_SKIP
    ))
    if extra_buttons:
        builder.attach(InlineKeyboardBuilder.from_markup(extra_buttons))

    return builder.as_markup()


def get_time_selection_keyboard(
    prefix: str,
    start_hour: int = 8,
    end_hour: int = 19,
    extra_buttons: InlineKeyboardMarkup | None = None
) -> InlineKeyboardMarkup:
    """Создаёт клавиатуру выбора времени."""
    builder = InlineKeyboardBuilder()

    row_buttons = []
    for hour in range(start_hour, end_hour + 1):
        row_buttons.append(InlineKeyboardButton(
            text=f"{hour:02d}:00",
            callback_data=f"{prefix}:hour:{hour}"
        ))
        if len(row_buttons) == 4:
            builder.row(*row_buttons)
            row_buttons = []

    if row_buttons:
        builder.row(*row_buttons)

    if extra_buttons:
        for row in extra_buttons.inline_keyboard:
            builder.row(*row)

    return builder.as_markup()
