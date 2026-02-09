"""Обработчики главного меню пользователя."""

from aiogram import Router, F
from aiogram.types import Message
from sqlalchemy import select

from core.logger import setup_logging

from database.models import Employee, AbsenceRequest
from bot.lexicon.lexicon import status_icons, type_names

router = Router()

logger = setup_logging(__name__)


@router.message(F.text == "👤 Профиль")
async def profile(message: Message, session):
    """Показывает профиль пользователя."""

    result = await session.execute(
        select(Employee).where(Employee.telegram_id == message.from_user.id)
    )
    employee = result.scalar_one_or_none()

    if not employee:
        await message.answer("❌ Профиль не найден")
        return

    logger.info("Показ профиля пользователя")
    await message.answer(
        f"👤 <b>Ваш профиль</b>\n\n"
        f"📛 {employee.last_name} {employee.name}\n"
        f"📧 {employee.email}\n"
        f"💼 {employee.position or 'Не указана'}\n"
        f"🎭 Роль: {employee.role}"
    )


@router.message(F.text == "📋 Мои заявки")
async def my_requests(message: Message, session):
    """Показывает заявки пользователя."""

    result = await session.execute(
        select(Employee).where(Employee.telegram_id == message.from_user.id)
    )
    employee = result.scalar_one_or_none()

    if not employee:
        await message.answer("❌ Профиль не найден")
        return

    logger.info("Показ заявок пользователя")
    result = await session.execute(
        select(AbsenceRequest)
        .where(AbsenceRequest.employee_id == employee.id)
        .order_by(AbsenceRequest.created_at.desc())
        .limit(10)
    )
    requests = result.scalars().all()

    if not requests:
        await message.answer("📋 У вас пока нет заявок")
        return

    text = "📋 <b>Ваши заявки:</b>\n\n"
    for req in requests:

        logger.debug(
            f"Заявка: {req.id}, статус: {req.status}, "
            f"тип: {req.request_type}"
        )

        icon = status_icons.get(req.status, "❓")
        type_name = type_names.get(req.request_type, req.request_type)
        text += (
            f"{icon} <b>{type_name}</b>\n"
            f"   📅 {req.start_date} — {req.end_date}\n"
            f"   💬 {req.comment or 'Без комментария'}\n\n"
        )
    logger.info("Отправка списка заявок пользователю")
    await message.answer(text)
