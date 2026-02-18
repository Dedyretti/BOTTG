from datetime import datetime

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.exceptions import TelegramBadRequest

from bot.services.notifications import NotificationService
from bot.states.states_fsm import CreateRequestStates
from bot.keyboards.user.inline_keyboards import (
    get_cancel_keyboard,
    get_back_cancel_keyboard,
    get_request_type_keyboard,
)
from bot.lexicon.lexicon import (
    REQUEST_TYPE_LABELS,
    MenuButtons,
    CallbackData,
    RequestMessages,
)
from bot.utils.utils import (
    get_menu_by_role,
    format_request_preview,
    safe_delete_message,
    safe_delete_by_id,
    send_new_message,
    hide_reply_keyboard,
    cleanup_state_messages,
)
from database.crud.employee import (
    get_employee_by_telegram_id,
    get_employee_role,
)

router = Router(name="request_base")


def get_edit_options_keyboard(request_type: str):
    """Создаёт клавиатуру с вариантами редактирования."""
    from bot.handlers.user.request_navigation import (
        get_edit_keyboard_by_type
    )
    return get_edit_keyboard_by_type(request_type)


@router.message(F.text == MenuButtons.SUBMIT_REQUEST)
async def start_request(message: Message, state: FSMContext) -> None:
    """Начинает процесс создания заявки."""
    await state.clear()
    await state.set_state(CreateRequestStates.choosing_type)
    await state.update_data(keyboard_type="type_selection")

    try:
        await message.delete()
    except TelegramBadRequest:
        pass

    await hide_reply_keyboard(message, state)

    cancel_kb = get_cancel_keyboard()
    text = f"{RequestMessages.NEW_REQUEST}\n\n{RequestMessages.CHOOSE_TYPE}"
    keyboard = get_request_type_keyboard(
        extra_buttons=cancel_kb.as_markup()
    )

    type_msg = await message.answer(
        text,
        reply_markup=keyboard
    )

    await state.update_data(type_message_id=type_msg.message_id)


@router.callback_query(F.data == CallbackData.CANCEL)
async def cancel_request(
    callback: CallbackQuery,
    state: FSMContext,
    session
) -> None:
    """Отменяет создание заявки."""
    bot = callback.bot
    chat_id = callback.message.chat.id

    await cleanup_state_messages(bot, chat_id, state)

    try:
        await callback.message.delete()
    except TelegramBadRequest:
        pass

    await state.clear()

    role = await get_employee_role(session, callback.from_user.id)

    await callback.message.answer(
        RequestMessages.REQUEST_CANCELLED,
        reply_markup=get_menu_by_role(role)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("req_type:"))
async def process_type(callback: CallbackQuery, state: FSMContext) -> None:
    """Обрабатывает выбор типа отсутствия."""
    data = await state.get_data()
    bot = callback.bot
    chat_id = callback.message.chat.id

    if "type_message_id" in data:
        await safe_delete_by_id(
            bot,
            chat_id,
            data["type_message_id"]
        )

    request_type = callback.data.split(":")[1]
    await state.update_data(request_type=request_type)
    await state.update_data(keyboard_type=f"date_selection_{request_type}")

    type_name = REQUEST_TYPE_LABELS.get(request_type, request_type)
    builder = get_back_cancel_keyboard()

    if request_type == "partial_absence":
        from bot.handlers.user.request_partial import (
            show_partial_date_selection
        )
        await show_partial_date_selection(
            callback,
            state,
            type_name,
            builder
        )
    else:
        from bot.handlers.user.request_full import show_start_date_selection
        await show_start_date_selection(
            callback,
            state,
            type_name,
            builder
        )


@router.callback_query(F.data == CallbackData.COMMENT_SKIP)
async def skip_comment(
    callback: CallbackQuery,
    state: FSMContext,
    session
) -> None:
    """Пропускает ввод комментария."""
    data = await state.get_data()

    if "request_type" not in data:
        await callback.answer(
            RequestMessages.ERROR_DATA_STALE,
            show_alert=True
        )
        await safe_delete_message(callback, state)
        await state.clear()

        role = await get_employee_role(session, callback.from_user.id)

        await callback.message.answer(
            MenuButtons.MAIN_MENU,
            reply_markup=get_menu_by_role(role)
        )
        return

    await state.update_data(comment=None)
    await state.update_data(keyboard_type="preview")

    from bot.handlers.user.request_navigation import show_request_preview
    await show_request_preview(callback, state)


@router.message(CreateRequestStates.entering_comment)
async def process_comment(message: Message, state: FSMContext) -> None:
    """Обрабатывает ввод комментария текстом."""
    comment = message.text.strip()
    if comment == "-":
        comment = None

    await state.update_data(comment=comment)
    await state.update_data(keyboard_type="preview")

    data = await state.get_data()
    await state.set_state(CreateRequestStates.confirming)

    try:
        await message.delete()
    except TelegramBadRequest:
        pass

    await send_new_message(
        message,
        format_request_preview(data),
        get_edit_options_keyboard(data["request_type"]),
        state
    )


@router.callback_query(F.data == CallbackData.CONFIRM)
async def confirm_request(
    callback: CallbackQuery,
    state: FSMContext,
    session,
    bot: Bot
) -> None:
    """Сохраняет заявку и отправляет уведомления."""
    data = await state.get_data()
    request_type = data["request_type"]
    if request_type == "partial_absence":
        from bot.handlers.user.request_partial import create_partial_request
        request = await create_partial_request(
            session,
            callback.from_user.id,
            data
        )
    else:
        from bot.handlers.user.request_full import create_full_request
        request = await create_full_request(
            session,
            callback.from_user.id,
            data
        )
    if not request:
        try:
            await callback.message.delete()
        except TelegramBadRequest:
            pass

        await state.clear()

        role = await get_employee_role(session, callback.from_user.id)

        await callback.message.answer(
            RequestMessages.ERROR_PROFILE_NOT_FOUND,
            reply_markup=get_menu_by_role(role)
        )
        await callback.answer()
        return

    employee = await get_employee_by_telegram_id(
        session,
        callback.from_user.id
    )

    notifier = NotificationService(bot)
    admin_results = await notifier.notify_admins_new_request(
        session,
        request,
        employee
    )

    chat_id = callback.message.chat.id
    await cleanup_state_messages(bot, chat_id, state)

    await state.clear()

    type_name = REQUEST_TYPE_LABELS.get(request_type, request_type)
    admin_count = len(admin_results['success'])

    if request_type == "partial_absence":
        start_dt = datetime.fromisoformat(data["start_date"])
        end_dt = datetime.fromisoformat(data["end_date"])

        success_text = RequestMessages.REQUEST_SUCCESS_PARTIAL.format(
            id=request.id,
            type=type_name,
            date=start_dt.strftime('%d.%m.%Y'),
            start_time=start_dt.strftime('%H:%M'),
            end_time=end_dt.strftime('%H:%M'),
            count=admin_count
        )
    else:
        start_dt = datetime.fromisoformat(data["start_date"])
        end_dt = datetime.fromisoformat(data["end_date"])

        success_text = RequestMessages.REQUEST_SUCCESS_FULL.format(
            id=request.id,
            type=type_name,
            start_date=start_dt.strftime('%d.%m.%Y'),
            end_date=end_dt.strftime('%d.%m.%Y'),
            count=admin_count
        )

    try:
        await callback.message.delete()
    except TelegramBadRequest:
        pass

    role = await get_employee_role(session, callback.from_user.id)

    await callback.message.answer(
        success_text,
        reply_markup=get_menu_by_role(role)
    )
    await callback.answer("✅ Заявка отправлена!")


@router.callback_query(F.data.startswith("partial:prev:"))
@router.callback_query(F.data.startswith("start:prev:"))
@router.callback_query(F.data.startswith("end:prev:"))
async def prev_month_handler(callback: CallbackQuery) -> None:
    """Обработчик предыдущего месяца для всех типов календарей."""
    from bot.keyboards.user.calendar import (
        get_calendar_keyboard,
        get_prev_month
    )

    prefix, _, year, month = callback.data.split(":")
    new_year, new_month = get_prev_month(int(year), int(month))

    await callback.message.edit_reply_markup(
        reply_markup=get_calendar_keyboard(
            new_year,
            new_month,
            prefix=prefix
        )
    )
    await callback.answer()


@router.callback_query(F.data.startswith("partial:next:"))
@router.callback_query(F.data.startswith("start:next:"))
@router.callback_query(F.data.startswith("end:next:"))
async def next_month_handler(callback: CallbackQuery) -> None:
    """Обработчик следующего месяца для всех типов календарей."""
    from bot.keyboards.user.calendar import (
        get_calendar_keyboard,
        get_next_month
    )

    prefix, _, year, month = callback.data.split(":")
    new_year, new_month = get_next_month(int(year), int(month))

    await callback.message.edit_reply_markup(
        reply_markup=get_calendar_keyboard(
            new_year,
            new_month,
            prefix=prefix
        )
    )
    await callback.answer()


@router.callback_query(F.data.startswith("partial:past:"))
@router.callback_query(F.data.startswith("start:past:"))
@router.callback_query(F.data.startswith("end:past:"))
async def past_date_alert(callback: CallbackQuery) -> None:
    """Алерт при попытке выбрать прошедшую дату."""
    await callback.answer(
        RequestMessages.ALERT_PAST_DATE,
        show_alert=True
    )


@router.callback_query(F.data.startswith("partial:ignore"))
@router.callback_query(F.data.startswith("start:ignore"))
@router.callback_query(F.data.startswith("end:ignore"))
async def ignore_button(callback: CallbackQuery) -> None:
    """Игнорировать нажатие на неактивную кнопку."""
    await callback.answer()
