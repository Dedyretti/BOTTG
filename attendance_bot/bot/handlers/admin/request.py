from aiogram import Router, F
from aiogram.types import Message

from sqlalchemy import select, func

from database.models import Employee, AbsenceRequest
from database.enums import RequestStatusEnum

from bot.lexicon.lexicon import type_names

router = Router()


@router.message(F.text == "📋 Новые заявки")
async def new_requests(message: Message, session):
    """Показывает список новых заявок."""

    result = await session.execute(
        select(AbsenceRequest)
        .where(AbsenceRequest.status == RequestStatusEnum.PENDING.value)
        .order_by(AbsenceRequest.created_at.desc())
    )
    requests = result.scalars().all()

    if not requests:
        await message.answer("✨ Нет новых заявок")
        return

    text = f"📋 <b>Новые заявки ({len(requests)}):</b>\n\n"
    for req in requests:
        employee = await session.get(Employee, req.employee_id)
        type_name = type_names.get(req.request_type, req.request_type)
        text += (
            f"👤 {employee.name} {employee.last_name}\n"
            f"📝 {type_name}\n"
            f"📅 {req.start_date} — {req.end_date}\n"
            f"─────────────────────\n"
        )

    await message.answer(text)


@router.message(F.text == "📁 Все заявки")
async def all_requests(message: Message, session):
    """Показывает все заявки."""

    result = await session.execute(
        select(func.count(AbsenceRequest.id))
    )
    total = result.scalar()

    await message.answer(
        f"📁 Всего заявок в системе: {total}\n\n"
        "🚧 Фильтры в разработке"
    )
