from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy import func, select

from bot.keyboards.admin.menu import requests_menu
from bot.keyboards.admin.request_keyboards import (
    get_reject_confirm_keyboard,
    get_request_view_keyboard,
)
from bot.lexicon.lexicon import type_names
from bot.services.notifications import NotificationService
from bot.states.states_fsm import RejectRequestStates
from database.crud.employee import get_employee_by_telegram_id
from database.crud.requests import (
    count_pending_requests,
    get_pending_requests_paginated,
    get_request_by_id,
    update_request_status,
)
from database.models import AbsenceRequest

router = Router()


@router.message(F.text == "📁 Все заявки")
async def all_requests(message: Message, session):
    """Показывает количество всех заявок."""

    result = await session.execute(
        select(func.count(AbsenceRequest.id))
    )
    total = result.scalar() or 0

    await message.answer(
        f"📁 <b>Всего заявок в системе:</b> {total}\n\n"
        "Используйте '📋 Новые заявки' для просмотра необработанных",
        reply_markup=requests_menu,
    )


@router.message(F.text == "📋 Новые заявки")
async def show_pending_requests(message: Message, session):
    """Показать список новых заявок."""

    total = await count_pending_requests(session)

    if total == 0:
        await message.answer(
            "✨ <b>Нет новых заявок</b>\n\n"
            "Все заявки обработаны.",
            reply_markup=requests_menu
        )
        return

    await _show_request_at_index(message, session, index=0, total=total)


async def _show_request_at_index(
    message: Message,
    session,
    index: int,
    total: int,
    edit: bool = False
):
    """Показать заявку по индексу."""

    requests = await get_pending_requests_paginated(
        session, offset=index, limit=1
    )

    if not requests:
        text = "✨ Нет новых заявок"
        if edit:
            await message.edit_text(text)
        else:
            await message.answer(text, reply_markup=requests_menu)
        return

    request = requests[0]
    text = _format_request_for_admin(request, index, total)
    keyboard = get_request_view_keyboard(request.id, index, total)

    if edit:
        await message.edit_text(text, reply_markup=keyboard)
    else:
        await message.answer(text, reply_markup=keyboard)


def _format_request_for_admin(request, index: int, total: int) -> str:
    """Форматировать заявку для просмотра админом."""

    employee = request.employee
    days = (request.end_date - request.start_date).days + 1
    type_name = type_names.get(
        request.request_type,
        request.request_type
    )
    full_name = f"{employee.last_name} {employee.name}"

    text = (
        f"⏳ <b>Заявка #{request.id}</b> (ожидает решения)\n\n"
        f"👤 <b>Сотрудник:</b> {full_name}\n"
        f"📧 {employee.email}\n\n"
        f"📌 <b>Тип:</b> {type_name}\n"
        f"📅 <b>Даты:</b> {request.start_date.strftime('%d.%m')} — "
        f"{request.end_date.strftime('%d.%m.%Y')} ({days} дн.)\n"
    )

    if request.comment:
        text += f"💬 <b>Комментарий:</b> {request.comment}\n"

    text += (
        f"\n🕐 <b>Подана:</b> "
        f"{request.created_at.strftime('%d.%m.%Y %H:%M')}\n\n"
        f"<i>Заявка {index + 1} из {total}</i>"
    )

    return text


@router.callback_query(F.data.startswith("req_nav:"))
async def navigate_requests(callback: CallbackQuery, session):
    """Навигация между заявками."""

    _, index_str = callback.data.split(":")

    if index_str == "ignore":
        await callback.answer()
        return

    index = int(index_str)
    total = await count_pending_requests(session)

    await _show_request_at_index(
        callback.message, session, index, total, edit=True
    )
    await callback.answer()


@router.callback_query(F.data == "req_back_to_menu")
async def back_to_requests_menu(callback: CallbackQuery):
    """Вернуться в меню заявок."""

    await callback.message.delete()
    await callback.message.answer(
        "📁 Меню заявок",
        reply_markup=requests_menu
    )
    await callback.answer()


@router.callback_query(F.data.startswith("req_approve:"))
async def approve_request(callback: CallbackQuery, session, bot: Bot):
    """Одобрить заявку."""

    request_id = int(callback.data.split(":")[1])

    request = await get_request_by_id(session, request_id)

    if not request:
        await callback.answer("❌ Заявка не найдена", show_alert=True)
        return

    if request.status != "pending":
        await callback.answer(
            "❌ Заявка уже обработана",
            show_alert=True
        )
        await callback.message.edit_reply_markup(reply_markup=None)
        return

    admin = await get_employee_by_telegram_id(
        session,
        callback.from_user.id
    )
    if not admin:
        await callback.answer(
            "❌ Ошибка авторизации",
            show_alert=True
        )
        return

    await update_request_status(
        session,
        request_id=request_id,
        new_status="approved",
        changed_by_id=admin.id
    )

    admin_name = f"{admin.last_name} {admin.name}"

    new_text = (
        f"{callback.message.text}\n\n"
        f"{'─' * 20}\n"
        f"✅ <b>ОДОБРЕНО</b>\n"
        f"👤 {admin_name}"
    )
    await callback.message.edit_text(new_text, reply_markup=None)

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


@router.callback_query(F.data.startswith("req_reject:"))
async def start_reject_request(
    callback: CallbackQuery,
    state: FSMContext,
    session
):
    """Начать процесс отклонения заявки."""

    request_id = int(callback.data.split(":")[1])

    request = await get_request_by_id(session, request_id)

    if not request:
        await callback.answer("❌ Заявка не найдена", show_alert=True)
        return

    if request.status != "pending":
        await callback.answer(
            "❌ Заявка уже обработана",
            show_alert=True
        )
        await callback.message.edit_reply_markup(reply_markup=None)
        return

    await state.update_data(
        reject_request_id=request_id,
        reject_message=callback.message
    )
    await state.set_state(RejectRequestStates.entering_reason)

    await callback.message.answer(
        "💬 <b>Введите причину отклонения заявки:</b>\n\n"
        "Напишите причину текстом или нажмите кнопку "
        "для отклонения без причины:",
        reply_markup=get_reject_confirm_keyboard(request_id)
    )
    await callback.answer()


@router.message(RejectRequestStates.entering_reason)
async def process_reject_reason(
    message: Message,
    state: FSMContext,
    session,
    bot: Bot
):
    """Обработать введенную причину отклонения."""

    data = await state.get_data()
    request_id = data.get("reject_request_id")
    reason = message.text.strip()

    request = await get_request_by_id(session, request_id)
    if not request:
        await message.answer("❌ Заявка не найдена")
        await state.clear()
        return

    admin = await get_employee_by_telegram_id(
        session,
        message.from_user.id
    )
    if not admin:
        await message.answer("❌ Ошибка авторизации")
        await state.clear()
        return

    await update_request_status(
        session,
        request_id=request_id,
        new_status="rejected",
        changed_by_id=admin.id,
        reason=reason
    )

    admin_name = f"{admin.last_name} {admin.name}"
    await message.answer(
        f"❌ <b>Заявка #{request_id} отклонена</b>\n"
        f"💬 Причина: {reason}\n"
        f"👤 Администратор: {admin_name}",
        reply_markup=requests_menu
    )

    notifier = NotificationService(bot)
    await notifier.update_admin_notifications(
        session, request, admin.id, "rejected"
    )

    if request.employee.telegram_id:
        await notifier.notify_user_request_rejected(
            request.employee.telegram_id,
            request,
            reason,
            admin_name
        )

    await state.clear()


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
    """Отклонить заявку без указания причины."""

    request_id = int(callback.data.split(":")[1])

    request = await get_request_by_id(session, request_id)
    if not request:
        await callback.answer(
            "❌ Заявка не найдена",
            show_alert=True
        )
        await state.clear()
        return

    admin = await get_employee_by_telegram_id(
        session,
        callback.from_user.id
    )
    if not admin:
        await callback.answer(
            "❌ Ошибка авторизации",
            show_alert=True
        )
        await state.clear()
        return

    await update_request_status(
        session,
        request_id=request_id,
        new_status="rejected",
        changed_by_id=admin.id,
        reason=None
    )

    await callback.message.delete()

    admin_name = f"{admin.last_name} {admin.name}"
    await callback.message.answer(
        f"❌ <b>Заявка #{request_id} отклонена</b>\n"
        f"Без указания причины\n"
        f"👤 Администратор: {admin_name}",
        reply_markup=requests_menu
    )

    notifier = NotificationService(bot)
    await notifier.update_admin_notifications(
        session, request, admin.id, "rejected"
    )

    if request.employee.telegram_id:
        await notifier.notify_user_request_rejected(
            request.employee.telegram_id,
            request,
            None,
            admin_name
        )

    await state.clear()
    await callback.answer("✅ Заявка отклонена")


@router.callback_query(F.data == "req_reject_cancel")
async def cancel_rejection(callback: CallbackQuery, state: FSMContext):
    """Отменить отклонение заявки."""

    await state.clear()
    await callback.message.delete()

    await callback.message.answer(
        "Отклонение заявки отменено",
        reply_markup=requests_menu
    )
    await callback.answer("Отменено")
