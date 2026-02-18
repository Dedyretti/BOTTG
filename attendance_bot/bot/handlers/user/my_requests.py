from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.exceptions import TelegramBadRequest


from core.logger import setup_logging
from database.crud.employee import (
    get_employee_role,
    get_employee_by_telegram_id
)
from database.crud.requests import (
    cancel_request_by_user,
    count_user_requests,
    get_request_by_id,
    get_user_requests_paginated,
)
from bot.lexicon.lexicon import (
    MenuButtons,
    RequestMessages,
    status_icons,
    status_names,
    type_names,
)
from bot.keyboards.user.inline_keyboards import (
    get_cancel_confirm_keyboard,
    get_user_request_keyboard,
)
from bot.services.notifications import NotificationService
from bot.utils.utils import get_menu_by_role

router = Router()
logger = setup_logging(__name__)


def format_user_request(request, index: int, total: int) -> str:
    """Форматирует заявку для просмотра пользователем."""

    status_icon = status_icons.get(request.status, "❓")
    status_name = status_names.get(request.status, request.status)
    type_name = type_names.get(request.request_type, request.request_type)

    if request.request_type == "partial_absence":
        dates = (
            f"{request.start_date.strftime('%d.%m.%Y')} "
            f"⏰ {request.start_date.strftime('%H:%M')} — "
            f"{request.end_date.strftime('%H:%M')}"
        )
    else:
        dates = (
            f"{request.start_date.strftime('%d.%m.%Y')} — "
            f"{request.end_date.strftime('%d.%m.%Y')}"
        )

    text = RequestMessages.MY_REQUESTS_HEADER.format(
        id=request.id,
        current=index + 1,
        total=total
    )

    text += RequestMessages.MY_REQUEST_INFO.format(
        status_icon=status_icon,
        status_name=status_name,
        type_name=type_name,
        dates=dates
    )

    if request.comment:
        text += RequestMessages.MY_REQUEST_COMMENT.format(
            comment=request.comment
        )

    text += RequestMessages.MY_REQUEST_CREATED.format(
        created_at=request.created_at.strftime('%d.%m.%Y %H:%M')
    )

    return text


async def show_request_at_index(
    message: Message,
    session,
    employee_id: int,
    index: int,
    edit: bool = False
) -> None:
    """Показывает заявку по индексу."""

    total = await count_user_requests(session, employee_id)

    if total == 0:
        text = RequestMessages.NO_REQUESTS
        if edit:
            await message.edit_text(text)
        else:
            await message.answer(text)
        return

    if index >= total:
        index = total - 1
    if index < 0:
        index = 0

    requests = await get_user_requests_paginated(
        session,
        employee_id,
        offset=index,
        limit=1
    )

    if not requests:
        return

    request = requests[0]
    text = format_user_request(request, index, total)

    can_cancel = request.status == "pending"
    keyboard = get_user_request_keyboard(
        request.id,
        index,
        total,
        can_cancel=can_cancel
    )

    if edit:
        try:
            await message.edit_text(text, reply_markup=keyboard)
        except TelegramBadRequest:
            pass
    else:
        await message.answer(text, reply_markup=keyboard)


@router.message(F.text == "📋 Мои заявки")
async def my_requests(message: Message, session, state: FSMContext):
    """Показывает заявки пользователя."""
    employee = await get_employee_by_telegram_id(session, message.from_user.id)

    if not employee:
        await message.answer(RequestMessages.PROFILE_NOT_FOUND)
        return

    total = await count_user_requests(session, employee.id)

    if total == 0:
        await message.answer(RequestMessages.NO_REQUESTS)
        return

    await state.update_data(
        employee_id=employee.id,
        current_index=0
    )

    await show_request_at_index(message, session, employee.id, 0)

    logger.info(f"Показ заявок пользователю {message.from_user.id}")


@router.callback_query(F.data.startswith("my_req:page:"))
async def paginate_requests(
    callback: CallbackQuery,
    session,
    state: FSMContext
):
    """Переключает страницу заявок."""
    index = int(callback.data.split(":")[2])

    data = await state.get_data()
    employee_id = data.get("employee_id")

    if not employee_id:
        employee = await get_employee_by_telegram_id(
            session,
            callback.from_user.id
            )
        if not employee:
            await callback.answer(
                RequestMessages.PROFILE_NOT_FOUND,
                show_alert=True
            )
            return
        employee_id = employee.id

    await state.update_data(current_index=index)

    await show_request_at_index(
        callback.message,
        session,
        employee_id,
        index,
        edit=True
    )
    await callback.answer()


@router.callback_query(F.data.startswith("my_req:cancel:"))
async def start_cancel_request(
    callback: CallbackQuery,
    session,
    state: FSMContext
):
    """Начинает процесс отмены заявки."""
    request_id = int(callback.data.split(":")[2])

    request = await get_request_by_id(session, request_id)

    if not request:
        await callback.answer(
            RequestMessages.REQUEST_CANCEL_ERROR,
            show_alert=True
        )
        return

    if request.status != "pending":
        await callback.answer(
            RequestMessages.REQUEST_ALREADY_PROCESSED,
            show_alert=True
        )
        return

    await state.update_data(
        cancel_request_id=request_id,
        prev_message_id=callback.message.message_id
    )

    await callback.message.edit_text(
        RequestMessages.REQUEST_CANCEL_CONFIRM.format(id=request_id),
        reply_markup=get_cancel_confirm_keyboard(request_id)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("my_req:cancel_confirm:"))
async def confirm_cancel_request(
    callback: CallbackQuery,
    session,
    state: FSMContext,
    bot: Bot
):
    """Подтверждает отмену заявки."""
    request_id = int(callback.data.split(":")[2])

    employee = await get_employee_by_telegram_id(
        session,
        callback.from_user.id
        )

    if not employee:
        await callback.answer(
            RequestMessages.PROFILE_NOT_FOUND,
            show_alert=True
        )
        return

    request = await cancel_request_by_user(session, request_id, employee.id)

    if not request:
        await callback.answer(
            RequestMessages.REQUEST_CANCEL_ERROR,
            show_alert=True
        )
        return

    notifier = NotificationService(bot)
    await notifier.notify_admins_request_cancelled(
        session,
        request,
        employee
    )

    await callback.answer(
        RequestMessages.REQUEST_CANCELLED_SUCCESS.format(id=request_id),
        show_alert=True
    )

    data = await state.get_data()
    current_index = data.get("current_index", 0)

    total = await count_user_requests(session, employee.id)

    if total == 0:
        try:
            await callback.message.delete()
        except TelegramBadRequest:
            pass

        role = await get_employee_role(session, callback.from_user.id)
        await callback.message.answer(
            RequestMessages.NO_REQUESTS,
            reply_markup=get_menu_by_role(role)
        )
        await state.clear()
        return

    if current_index >= total:
        current_index = total - 1

    await state.update_data(current_index=current_index)

    await show_request_at_index(
        callback.message,
        session,
        employee.id,
        current_index,
        edit=True
    )


@router.callback_query(F.data == "my_req:cancel_back")
async def cancel_back(
    callback: CallbackQuery,
    session,
    state: FSMContext
):
    """Возвращает к просмотру заявки."""
    data = await state.get_data()
    employee_id = data.get("employee_id")
    current_index = data.get("current_index", 0)

    if not employee_id:
        employee = await get_employee_by_telegram_id(
            session, callback.from_user.id)
        if employee:
            employee_id = employee.id

    if employee_id:
        await show_request_at_index(
            callback.message,
            session,
            employee_id,
            current_index,
            edit=True
        )

    await callback.answer()


@router.callback_query(F.data == "my_req:close")
async def close_requests(callback: CallbackQuery, session, state: FSMContext):
    """Закрывает просмотр заявок."""
    await state.clear()

    try:
        await callback.message.delete()
    except TelegramBadRequest:
        pass

    role = await get_employee_role(session, callback.from_user.id)

    await callback.message.answer(
        MenuButtons.MAIN_MENU,
        reply_markup=get_menu_by_role(role)
    )
    await callback.answer()


@router.callback_query(F.data == "my_req:ignore")
async def ignore_page_counter(callback: CallbackQuery):
    """Игнорирует нажатие на счётчик страниц."""
    await callback.answer()
