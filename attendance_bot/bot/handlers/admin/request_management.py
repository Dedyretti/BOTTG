from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, ReplyKeyboardRemove
from aiogram.exceptions import TelegramBadRequest

from bot.keyboards.admin.menu import requests_menu
from bot.keyboards.admin.inline_keyboards import (
    get_all_requests_pagination_keyboard,
)
from bot.keyboards.admin.request_keyboards import (
    get_reject_confirm_keyboard,
    get_request_view_keyboard,
)
from bot.lexicon.lexicon import AdminMessages, status_icons, type_names
from bot.services.notifications import NotificationService
from bot.states.states_fsm import RejectRequestStates
from database.crud.employee import get_employee_by_telegram_id
from database.crud.requests import (
    count_all_requests,
    count_pending_requests,
    get_all_requests_paginated,
    get_pending_requests_paginated,
    get_request_by_id,
    update_request_status,
)

router = Router()

REQUESTS_PER_PAGE = 5


async def _safe_delete_message(message: Message) -> None:
    """Безопасно удаляет сообщение."""
    try:
        await message.delete()
    except TelegramBadRequest:
        pass


async def _safe_delete_by_id(bot: Bot, chat_id: int, message_id: int) -> None:
    """Безопасно удаляет сообщение по ID."""
    try:
        await bot.delete_message(chat_id, message_id)
    except TelegramBadRequest:
        pass


async def _hide_reply_keyboard(message: Message) -> None:
    """Скрывает reply-клавиатуру."""
    hide_msg = await message.answer("⏳", reply_markup=ReplyKeyboardRemove())
    await _safe_delete_message(hide_msg)


async def _cleanup_state_messages(
    bot: Bot,
    chat_id: int,
    state: FSMContext
) -> None:
    """Удаляет все служебные сообщения из state."""
    data = await state.get_data()

    keys = [
        "request_message_id",
        "reason_message_id",
        "all_req_message_id"
    ]

    for key in keys:
        msg_id = data.get(key)
        if msg_id:
            await _safe_delete_by_id(bot, chat_id, msg_id)


def _get_total_pages(total: int, per_page: int = REQUESTS_PER_PAGE) -> int:
    """Вычисляет общее количество страниц."""
    return max(1, (total + per_page - 1) // per_page)


def _format_request_for_admin(request, index: int, total: int) -> str:
    """Форматирует заявку для просмотра админом."""
    employee = request.employee
    days = (request.end_date - request.start_date).days + 1
    type_name = type_names.get(request.request_type, request.request_type)
    full_name = f"{employee.last_name} {employee.name}"

    text = AdminMessages.REQUEST_VIEW.format(
        id=request.id,
        full_name=full_name,
        email=employee.email,
        type_name=type_name,
        start_date=request.start_date.strftime('%d.%m'),
        end_date=request.end_date.strftime('%d.%m.%Y'),
        days=days
    )

    if request.comment:
        text += AdminMessages.REQUEST_VIEW_COMMENT.format(
            comment=request.comment
        )

    text += AdminMessages.REQUEST_VIEW_FOOTER.format(
        created_at=request.created_at.strftime('%d.%m.%Y %H:%M'),
        current=index + 1,
        total=total
    )

    return text


def _format_requests_list(
    requests: list,
    page: int,
    total: int
) -> str:
    """Форматирует список заявок для пагинации."""
    total_pages = _get_total_pages(total)

    text = AdminMessages.ALL_REQUESTS_HEADER.format(
        current=page + 1,
        total=total_pages
    )

    for req in requests:
        status_icon = status_icons.get(req.status, "❓")
        type_name = type_names.get(req.request_type, req.request_type)
        full_name = f"{req.employee.last_name} {req.employee.name}"

        if req.request_type == "partial_absence":
            dates = (
                f"{req.start_date.strftime('%d.%m.%Y')} "
                f"{req.start_date.strftime('%H:%M')}-"
                f"{req.end_date.strftime('%H:%M')}"
            )
        else:
            dates = (
                f"{req.start_date.strftime('%d.%m')} — "
                f"{req.end_date.strftime('%d.%m.%Y')}"
            )

        text += AdminMessages.REQUEST_LIST_ITEM.format(
            status_icon=status_icon,
            id=req.id,
            type_name=type_name,
            full_name=full_name,
            dates=dates
        )
        text += "\n"

    return text


def _get_admin_full_name(admin) -> str:
    """Возвращает полное имя админа."""
    return f"{admin.last_name} {admin.name}"


async def _show_request_at_index(
    message: Message,
    session,
    index: int,
    total: int,
    edit: bool = False,
    state: FSMContext | None = None
):
    """Показывает заявку по индексу."""
    requests = await get_pending_requests_paginated(
        session,
        offset=index,
        limit=1
    )

    if not requests:
        if edit:
            try:
                await message.edit_text(AdminMessages.NO_REQUESTS_LEFT)
            except TelegramBadRequest:
                pass
        else:
            await message.answer(
                AdminMessages.NO_REQUESTS_LEFT,
                reply_markup=requests_menu
            )

        if state:
            await state.clear()
        return

    request = requests[0]
    text = _format_request_for_admin(request, index, total)
    keyboard = get_request_view_keyboard(request.id, index, total)

    if edit:
        try:
            await message.edit_text(text, reply_markup=keyboard)
        except TelegramBadRequest:
            pass
    else:
        sent = await message.answer(text, reply_markup=keyboard)
        if state:
            await state.update_data(request_message_id=sent.message_id)


@router.message(F.text == "📁 Все заявки")
async def all_requests(message: Message, session, state: FSMContext, bot: Bot):
    """Показывает все заявки с пагинацией."""
    chat_id = message.chat.id
    await _cleanup_state_messages(bot, chat_id, state)

    total = await count_all_requests(session)

    if total == 0:
        await message.answer(AdminMessages.ALL_REQUESTS_EMPTY)
        return

    await _safe_delete_message(message)
    await _hide_reply_keyboard(message)

    page = 0
    requests = await get_all_requests_paginated(
        session,
        offset=0,
        limit=REQUESTS_PER_PAGE
    )

    total_pages = _get_total_pages(total)
    text = _format_requests_list(requests, page, total)
    keyboard = get_all_requests_pagination_keyboard(page, total_pages)

    sent = await message.answer(text, reply_markup=keyboard)
    await state.update_data(
        all_req_page=page,
        all_req_message_id=sent.message_id
    )


@router.callback_query(F.data.startswith("all_req:page:"))
async def paginate_all_requests(
    callback: CallbackQuery,
    session,
    state: FSMContext
):
    """Переключает страницу всех заявок."""
    page = int(callback.data.split(":")[2])

    total = await count_all_requests(session)

    if total == 0:
        await callback.answer(
            AdminMessages.ALL_REQUESTS_EMPTY,
            show_alert=True
        )
        return

    requests = await get_all_requests_paginated(
        session,
        offset=page * REQUESTS_PER_PAGE,
        limit=REQUESTS_PER_PAGE
    )

    if not requests:
        await callback.answer("Заявок больше нет", show_alert=True)
        return

    total_pages = _get_total_pages(total)
    text = _format_requests_list(requests, page, total)
    keyboard = get_all_requests_pagination_keyboard(page, total_pages)

    await state.update_data(all_req_page=page)

    try:
        await callback.message.edit_text(text, reply_markup=keyboard)
    except TelegramBadRequest:
        pass

    await callback.answer()


@router.callback_query(F.data == "all_req:close")
async def close_all_requests(
    callback: CallbackQuery,
    state: FSMContext
):
    """Закрывает просмотр всех заявок."""
    await state.clear()
    await _safe_delete_message(callback.message)

    await callback.message.answer(
        AdminMessages.REQUESTS_MENU_TITLE,
        reply_markup=requests_menu
    )
    await callback.answer()


@router.callback_query(F.data == "all_req:ignore")
async def ignore_all_req_counter(callback: CallbackQuery):
    """Игнорирует нажатие на счётчик страниц."""
    await callback.answer()


@router.message(F.text == "📋 Новые заявки")
async def show_pending_requests(
    message: Message,
    session,
    state: FSMContext,
    bot: Bot
):
    """Показывает список новых заявок."""
    chat_id = message.chat.id
    await _cleanup_state_messages(bot, chat_id, state)

    total = await count_pending_requests(session)

    if total == 0:
        await message.answer(
            AdminMessages.NO_PENDING_REQUESTS,
            reply_markup=requests_menu
        )
        return

    await _safe_delete_message(message)
    await _hide_reply_keyboard(message)

    await state.update_data(current_index=0)
    await _show_request_at_index(
        message,
        session,
        index=0,
        total=total,
        state=state
    )


@router.callback_query(F.data.startswith("req_nav:"))
async def navigate_requests(
    callback: CallbackQuery,
    session,
    state: FSMContext
):
    """Навигация между заявками."""
    _, index_str = callback.data.split(":")

    if index_str == "ignore":
        await callback.answer()
        return

    index = int(index_str)
    total = await count_pending_requests(session)

    await state.update_data(current_index=index)

    await _show_request_at_index(
        callback.message,
        session,
        index,
        total,
        edit=True,
        state=state
    )
    await callback.answer()


@router.callback_query(F.data == "req_back_to_menu")
async def back_to_requests_menu(callback: CallbackQuery, state: FSMContext):
    """Возвращает в меню заявок."""
    await state.clear()
    await _safe_delete_message(callback.message)

    await callback.message.answer(
        AdminMessages.REQUESTS_MENU_TITLE,
        reply_markup=requests_menu
    )
    await callback.answer()


@router.callback_query(F.data.startswith("req_approve:"))
async def approve_request(
    callback: CallbackQuery,
    session,
    bot: Bot,
    state: FSMContext
):
    """Одобряет заявку."""
    request_id = int(callback.data.split(":")[1])

    request = await get_request_by_id(session, request_id)

    if not request:
        await callback.answer(
            AdminMessages.ERROR_REQUEST_NOT_FOUND,
            show_alert=True
        )
        return

    if request.status != "pending":
        await callback.answer(
            AdminMessages.ERROR_REQUEST_ALREADY_PROCESSED,
            show_alert=True
        )
        try:
            await callback.message.edit_reply_markup(reply_markup=None)
        except TelegramBadRequest:
            pass
        return

    admin = await get_employee_by_telegram_id(session, callback.from_user.id)

    if not admin:
        await callback.answer(AdminMessages.ERROR_AUTH, show_alert=True)
        return

    await update_request_status(
        session,
        request_id=request_id,
        new_status="approved",
        changed_by_id=admin.id
    )

    admin_name = _get_admin_full_name(admin)

    notifier = NotificationService(bot)
    await notifier.update_admin_notifications(
        session,
        request,
        admin.id,
        "approved",
        admin_name
    )

    if request.employee.telegram_id:
        await notifier.notify_user_request_approved(
            request.employee.telegram_id,
            request,
            admin_name
        )

    await callback.answer("✅ Заявка одобрена")

    data = await state.get_data()
    current_index = data.get("current_index", 0)
    total = await count_pending_requests(session)

    if total == 0:
        try:
            await callback.message.edit_text(AdminMessages.NO_REQUESTS_LEFT)
        except TelegramBadRequest:
            pass

        await callback.message.answer(
            AdminMessages.REQUESTS_MENU_TITLE,
            reply_markup=requests_menu
        )
        await state.clear()
        return

    if current_index >= total:
        current_index = total - 1

    await state.update_data(current_index=current_index)
    await _show_request_at_index(
        callback.message,
        session,
        current_index,
        total,
        edit=True,
        state=state
    )


@router.callback_query(F.data.startswith("req_reject:"))
async def start_reject_request(
    callback: CallbackQuery,
    state: FSMContext,
    session
):
    """Начинает процесс отклонения заявки."""
    request_id = int(callback.data.split(":")[1])

    request = await get_request_by_id(session, request_id)

    if not request:
        await callback.answer(
            AdminMessages.ERROR_REQUEST_NOT_FOUND,
            show_alert=True
        )
        return

    if request.status != "pending":
        await callback.answer(
            AdminMessages.ERROR_REQUEST_ALREADY_PROCESSED,
            show_alert=True
        )
        try:
            await callback.message.edit_reply_markup(reply_markup=None)
        except TelegramBadRequest:
            pass
        return

    data = await state.get_data()
    current_index = data.get("current_index", 0)

    await state.update_data(
        reject_request_id=request_id,
        reject_message_id=callback.message.message_id,
        current_index=current_index
    )
    await state.set_state(RejectRequestStates.entering_reason)

    reason_msg = await callback.message.answer(
        AdminMessages.ENTER_REJECT_REASON,
        reply_markup=get_reject_confirm_keyboard(request_id)
    )
    await state.update_data(reason_message_id=reason_msg.message_id)

    await callback.answer()


@router.message(RejectRequestStates.entering_reason)
async def process_reject_reason(
    message: Message,
    state: FSMContext,
    session,
    bot: Bot
):
    """Обрабатывает введенную причину отклонения."""
    data = await state.get_data()
    request_id = data.get("reject_request_id")
    reason = message.text.strip()
    current_index = data.get("current_index", 0)
    reject_message_id = data.get("reject_message_id")
    reason_message_id = data.get("reason_message_id")
    chat_id = message.chat.id

    await _safe_delete_message(message)

    if reason_message_id:
        await _safe_delete_by_id(bot, chat_id, reason_message_id)

    request = await get_request_by_id(session, request_id)

    if not request:
        await message.answer(
            AdminMessages.ERROR_REQUEST_NOT_FOUND,
            reply_markup=requests_menu
        )
        await state.clear()
        return

    admin = await get_employee_by_telegram_id(session, message.from_user.id)

    if not admin:
        await message.answer(
            AdminMessages.ERROR_AUTH,
            reply_markup=requests_menu
        )
        await state.clear()
        return

    await update_request_status(
        session,
        request_id=request_id,
        new_status="rejected",
        changed_by_id=admin.id,
        reason=reason
    )

    admin_name = _get_admin_full_name(admin)

    notifier = NotificationService(bot)

    await notifier.update_admin_notifications(
        session,
        request,
        admin.id,
        "rejected",
        admin_name,
        reason
    )

    if request.employee and request.employee.telegram_id:
        await notifier.notify_user_request_rejected(
            request.employee.telegram_id,
            request,
            reason,
            admin_name
        )

    total = await count_pending_requests(session)

    if total == 0:
        if reject_message_id:
            try:
                await bot.edit_message_text(
                    AdminMessages.NO_REQUESTS_LEFT,
                    chat_id=chat_id,
                    message_id=reject_message_id
                )
            except TelegramBadRequest:
                pass

        await message.answer(
            AdminMessages.REQUESTS_MENU_TITLE,
            reply_markup=requests_menu
        )
        await state.clear()
        return

    if current_index >= total:
        current_index = total - 1

    await state.clear()
    await state.update_data(current_index=current_index)

    if reject_message_id:
        requests_list = await get_pending_requests_paginated(
            session,
            offset=current_index,
            limit=1
        )

        if requests_list:
            req = requests_list[0]
            text = _format_request_for_admin(req, current_index, total)
            keyboard = get_request_view_keyboard(
                req.id,
                current_index,
                total
            )

            try:
                await bot.edit_message_text(
                    text,
                    chat_id=chat_id,
                    message_id=reject_message_id,
                    reply_markup=keyboard
                )
            except TelegramBadRequest:
                pass


@router.callback_query(
    F.data.startswith("req_reject_confirm:"),
    RejectRequestStates.entering_reason
)
async def reject_without_reason(
    callback: CallbackQuery,
    state: FSMContext,
    session,
    bot: Bot
):
    """Отклоняет заявку без указания причины."""
    request_id = int(callback.data.split(":")[1])
    data = await state.get_data()
    current_index = data.get("current_index", 0)
    reject_message_id = data.get("reject_message_id")
    chat_id = callback.message.chat.id

    request = await get_request_by_id(session, request_id)

    if not request:
        await callback.answer(
            AdminMessages.ERROR_REQUEST_NOT_FOUND,
            show_alert=True
        )
        await state.clear()
        return

    admin = await get_employee_by_telegram_id(session, callback.from_user.id)

    if not admin:
        await callback.answer(AdminMessages.ERROR_AUTH, show_alert=True)
        await state.clear()
        return

    await update_request_status(
        session,
        request_id=request_id,
        new_status="rejected",
        changed_by_id=admin.id,
        reason=None
    )

    admin_name = _get_admin_full_name(admin)

    notifier = NotificationService(bot)

    await notifier.update_admin_notifications(
        session,
        request,
        admin.id,
        "rejected",
        admin_name
    )

    if request.employee.telegram_id:
        await notifier.notify_user_request_rejected(
            request.employee.telegram_id,
            request,
            None,
            admin_name
        )

    await callback.answer("✅ Заявка отклонена")

    await _safe_delete_message(callback.message)

    total = await count_pending_requests(session)

    if total == 0:
        if reject_message_id:
            try:
                await bot.edit_message_text(
                    AdminMessages.NO_REQUESTS_LEFT,
                    chat_id=chat_id,
                    message_id=reject_message_id
                )
            except TelegramBadRequest:
                pass

        await callback.message.answer(
            AdminMessages.REQUESTS_MENU_TITLE,
            reply_markup=requests_menu
        )
        await state.clear()
        return

    if current_index >= total:
        current_index = total - 1

    await state.clear()
    await state.update_data(current_index=current_index)

    if reject_message_id:
        requests_list = await get_pending_requests_paginated(
            session,
            offset=current_index,
            limit=1
        )

        if requests_list:
            req = requests_list[0]
            text = _format_request_for_admin(req, current_index, total)
            keyboard = get_request_view_keyboard(
                req.id,
                current_index,
                total
            )

            try:
                await bot.edit_message_text(
                    text,
                    chat_id=chat_id,
                    message_id=reject_message_id,
                    reply_markup=keyboard
                )
            except TelegramBadRequest:
                pass


@router.callback_query(F.data == "req_reject_cancel")
async def cancel_rejection(callback: CallbackQuery, state: FSMContext):
    """Отменяет отклонение заявки."""
    await state.set_state(None)

    data = await state.get_data()
    current_index = data.get("current_index", 0)

    await state.update_data(current_index=current_index)

    await _safe_delete_message(callback.message)

    await callback.answer("Отменено")
