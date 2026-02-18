from datetime import datetime

from aiogram import Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    Message,
    ReplyKeyboardRemove,
)
from aiogram.exceptions import TelegramBadRequest

from bot.keyboards.admin.menu import admin_menu
from bot.keyboards.user.reply_keyboards import user_menu
from bot.lexicon.lexicon import (
    REQUEST_TYPE_LABELS,
    RequestMessages,
    status_icons,
    type_names,
)
from database.models import AbsenceRequest

REQUESTS_PER_PAGE = 3


def get_menu_by_role(role: str | None):
    """Возвращает клавиатуру меню по роли."""
    if role in ("admin", "superuser"):
        return admin_menu
    return user_menu


def format_request(req: AbsenceRequest) -> str:
    """Форматирует одну заявку для отображения."""
    icon = status_icons.get(req.status, "❓")
    type_name = type_names.get(req.request_type, req.request_type)

    if req.request_type == "partial_absence":
        date_str = (
            f"📅 {req.start_date.strftime('%d.%m.%Y')} "
            f"⏰ {req.start_date.strftime('%H:%M')} — "
            f"{req.end_date.strftime('%H:%M')}"
        )
    else:
        date_str = (
            f"📅 {req.start_date.strftime('%d.%m.%Y')} — "
            f"{req.end_date.strftime('%d.%m.%Y')}"
        )

    return (
        f"{icon} <b>{type_name}</b>\n"
        f"   {date_str}\n"
        f"   💬 {req.comment or 'Без комментария'}\n"
    )


def get_total_pages(total: int) -> int:
    """Вычисляет общее количество страниц."""
    return max(1, (total + REQUESTS_PER_PAGE - 1) // REQUESTS_PER_PAGE)


def build_page_text(
    requests: list[AbsenceRequest],
    page: int,
    total: int
) -> str:
    """Формирует текст страницы с заявками."""
    total_pages = get_total_pages(total)

    text = (
        f"📋 <b>Ваши заявки</b> "
        f"(стр. {page + 1}/{total_pages}, всего: {total}):\n\n"
    )

    for req in requests:
        text += format_request(req) + "\n"

    return text


def format_request_preview(data: dict) -> str:
    """Форматирует предпросмотр заявки."""
    type_name = REQUEST_TYPE_LABELS.get(
        data["request_type"],
        data["request_type"]
    )
    comment = data.get("comment", RequestMessages.COMMENT_SKIPPED)

    if data["request_type"] == "partial_absence":
        start_dt = datetime.fromisoformat(data["start_date"])
        end_dt = datetime.fromisoformat(data["end_date"])

        preview = RequestMessages.REQUEST_FORMAT_PARTIAL.format(
            type=type_name,
            date=start_dt.strftime('%d.%m.%Y'),
            start_time=start_dt.strftime('%H:%M'),
            end_time=end_dt.strftime('%H:%M'),
            comment=comment
        )
    else:
        start_dt = datetime.fromisoformat(data["start_date"])
        end_dt = datetime.fromisoformat(data["end_date"])

        preview = RequestMessages.REQUEST_FORMAT_FULL.format(
            type=type_name,
            start_date=start_dt.strftime('%d.%m.%Y'),
            end_date=end_dt.strftime('%d.%m.%Y'),
            comment=comment
        )

    return f"{RequestMessages.PREVIEW_REQUEST}\n\n{preview}"


async def safe_delete_message(
    message: Message | CallbackQuery,
    state: FSMContext
) -> None:
    """Безопасно удаляет предыдущее сообщение с клавиатурой."""
    data = await state.get_data()
    old_message_id = data.get("keyboard_message_id")

    if old_message_id:
        try:
            if isinstance(message, CallbackQuery):
                chat_id = message.message.chat.id
            else:
                chat_id = message.chat.id

            await message.bot.delete_message(chat_id, old_message_id)
        except (TelegramBadRequest, AttributeError):
            pass

    await state.update_data(keyboard_message_id=None)


async def safe_delete_by_id(
    bot: Bot,
    chat_id: int,
    message_id: int
) -> None:
    """Безопасно удаляет сообщение по ID."""
    try:
        await bot.delete_message(chat_id, message_id)
    except (TelegramBadRequest, AttributeError):
        pass


async def send_new_message(
    target: Message | CallbackQuery,
    text: str,
    reply_markup,
    state: FSMContext
) -> Message:
    """Отправляет новое сообщение и сохраняет его ID."""
    await safe_delete_message(target, state)

    if isinstance(target, CallbackQuery):
        sent = await target.message.answer(
            text,
            reply_markup=reply_markup
        )
    else:
        sent = await target.answer(
            text,
            reply_markup=reply_markup
        )

    await state.update_data(keyboard_message_id=sent.message_id)
    return sent


async def hide_reply_keyboard(
    message: Message,
    state: FSMContext
) -> None:
    """Скрывает reply-клавиатуру."""
    hide_msg = await message.answer(
        "⏳",
        reply_markup=ReplyKeyboardRemove()
    )
    await safe_delete_by_id(
        message.bot,
        message.chat.id,
        hide_msg.message_id
    )


async def cleanup_state_messages(
    bot: Bot,
    chat_id: int,
    state: FSMContext
) -> None:
    """Удаляет все служебные сообщения из state."""
    data = await state.get_data()

    for key in ("type_message_id", "keyboard_message_id"):
        msg_id = data.get(key)
        if msg_id:
            await safe_delete_by_id(bot, chat_id, msg_id)
