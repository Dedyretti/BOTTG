from aiogram import Bot, F, Router
from aiogram.types import CallbackQuery, Message

from bot.keyboards.user.menu import user_menu
from bot.keyboards.user.request import (
    get_cancel_confirm_keyboard,
    get_user_request_keyboard,
)
from bot.lexicon.lexicon import type_names
from bot.services.notifications import NotificationService
from database.crud.employee import get_employee_by_telegram_id
from database.crud.requests import (
    cancel_user_request,
    count_user_pending_requests,
    get_user_pending_requests,
)

router = Router()


@router.message(F.text == "📋 Мои заявки")
async def show_my_requests(message: Message, session):
    """Показать заявки пользователя."""

    total = await count_user_pending_requests(
        session,
        message.from_user.id
    )

    if total == 0:
        await message.answer(
            "📭 <b>У вас нет активных заявок</b>\n\n"
            "Все ваши заявки обработаны или отменены.",
            reply_markup=user_menu
        )
        return

    await _show_user_request_at_index(
        message,
        session,
        message.from_user.id,
        index=0,
        total=total
    )


async def _show_user_request_at_index(
    message: Message,
    session,
    telegram_id: int,
    index: int,
    total: int,
    edit: bool = False
):
    """Показать заявку пользователя по индексу."""

    requests = await get_user_pending_requests(
        session,
        telegram_id,
        offset=index,
        limit=1
    )

    if not requests:
        text = "📭 Нет активных заявок"
        if edit:
            await message.edit_text(text)
        else:
            await message.answer(text, reply_markup=user_menu)
        return

    request = requests[0]
    text = _format_user_request(request, index, total)
    keyboard = get_user_request_keyboard(request.id, index, total)

    if edit:
        await message.edit_text(text, reply_markup=keyboard)
    else:
        await message.answer(text, reply_markup=keyboard)


def _format_user_request(request, index: int, total: int) -> str:
    """Форматировать заявку для пользователя."""

    days = (request.end_date - request.start_date).days + 1
    type_name = type_names.get(
        request.request_type,
        request.request_type
    )

    text = (
        f"⏳ <b>Заявка #{request.id}</b>\n\n"
        f"📌 <b>Тип:</b> {type_name}\n"
        f"📅 <b>Период:</b> "
        f"{request.start_date.strftime('%d.%m.%Y')} — "
        f"{request.end_date.strftime('%d.%m.%Y')} ({days} дн.)\n"
        f"📝 <b>Статус:</b> Ожидает рассмотрения\n"
    )

    if request.comment:
        text += f"💬 <b>Ваш комментарий:</b> {request.comment}\n"

    text += (
        f"\n🕐 <b>Подана:</b> "
        f"{request.created_at.strftime('%d.%m.%Y %H:%M')}\n\n"
        f"<i>Заявка {index + 1} из {total}</i>\n\n"
        "💡 <i>Вы можете отменить заявку до её рассмотрения</i>"
    )

    return text


@router.callback_query(F.data.startswith("user_req_nav:"))
async def navigate_user_requests(callback: CallbackQuery, session):
    """Навигация по заявкам пользователя."""

    _, index_str = callback.data.split(":")

    if index_str == "ignore":
        await callback.answer()
        return

    index = int(index_str)
    total = await count_user_pending_requests(
        session,
        callback.from_user.id
    )

    await _show_user_request_at_index(
        callback.message,
        session,
        callback.from_user.id,
        index,
        total,
        edit=True
    )
    await callback.answer()


@router.callback_query(F.data.startswith("user_cancel_req:"))
async def start_cancel_request(callback: CallbackQuery):
    """Начать процесс отмены заявки."""

    request_id = int(callback.data.split(":")[1])

    await callback.message.edit_text(
        f"❓ <b>Подтверждение отмены</b>\n\n"
        f"Вы действительно хотите отменить заявку #{request_id}?\n\n"
        f"⚠️ <i>Это действие нельзя будет отменить</i>",
        reply_markup=get_cancel_confirm_keyboard(request_id)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("user_confirm_cancel:"))
async def confirm_cancel_request(
    callback: CallbackQuery,
    session,
    bot: Bot
):
    """Подтвердить отмену заявки."""

    request_id = int(callback.data.split(":")[1])

    request = await cancel_user_request(
        session,
        request_id,
        callback.from_user.id
    )

    if not request:
        await callback.message.edit_text(
            "❌ Не удалось отменить заявку.\n"
            "Возможно, она уже обработана."
        )
        await callback.answer()
        return

    employee = await get_employee_by_telegram_id(
        session,
        callback.from_user.id
    )

    notifier = NotificationService(bot)
    await notifier.notify_admins_request_cancelled(
        session,
        request,
        employee
    )

    await callback.message.edit_text(
        f"🚫 <b>Заявка #{request_id} отменена</b>\n\n"
        "Администраторы уведомлены об отмене."
    )

    await callback.message.answer(
        "Главное меню:",
        reply_markup=user_menu
    )
    await callback.answer("✅ Заявка отменена")


@router.callback_query(F.data == "user_cancel_back")
async def cancel_back(callback: CallbackQuery, session):
    """Вернуться к просмотру заявок."""

    total = await count_user_pending_requests(
        session,
        callback.from_user.id
    )

    if total > 0:
        await _show_user_request_at_index(
            callback.message,
            session,
            callback.from_user.id,
            index=0,
            total=total,
            edit=True
        )
    else:
        await callback.message.edit_text(
            "📭 У вас нет активных заявок"
        )
        await callback.message.answer(
            "Главное меню:",
            reply_markup=user_menu
        )

    await callback.answer("Отмена отменена 😊")


@router.callback_query(F.data == "user_back_menu")
async def back_to_menu(callback: CallbackQuery):
    """Вернуться в главное меню."""

    await callback.message.delete()
    await callback.message.answer(
        "Главное меню:",
        reply_markup=user_menu
    )
    await callback.answer()
