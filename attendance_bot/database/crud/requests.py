from datetime import date, datetime
from typing import Literal

import pytz
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database.enums import ChangeTypeEnum, RequestStatusEnum
from database.models import AbsenceRequest, AbsenceRequestHistory, Employee

LOCAL_TIMEZONE = pytz.timezone('Europe/Moscow')


def ensure_timezone(dt: datetime | date) -> datetime:
    """Преобразует date/datetime в datetime с таймзоной."""
    if isinstance(dt, date) and not isinstance(dt, datetime):
        dt = datetime.combine(dt, datetime.min.time())

    if dt.tzinfo is None:
        return LOCAL_TIMEZONE.localize(dt)
    return dt


async def create_absence_request(
    session: AsyncSession,
    telegram_id: int,
    request_type: str,
    start_date: datetime | date,
    end_date: datetime | date,
    comment: str | None = None
) -> AbsenceRequest | None:
    """Создаёт новую заявку на отсутствие."""
    result = await session.execute(
        select(Employee).where(Employee.telegram_id == telegram_id)
    )
    employee = result.scalar_one_or_none()

    if not employee:
        return None

    request = AbsenceRequest(
        employee_id=employee.id,
        request_type=request_type,
        start_date=ensure_timezone(start_date),
        end_date=ensure_timezone(end_date),
        comment=comment,
        status="pending"
    )

    session.add(request)
    await session.commit()
    await session.refresh(request)

    return request


async def get_request_by_id(
    session: AsyncSession,
    request_id: int
) -> AbsenceRequest | None:
    """Получает заявку по ID с данными сотрудника."""
    result = await session.execute(
        select(AbsenceRequest)
        .options(selectinload(AbsenceRequest.employee))
        .where(AbsenceRequest.id == request_id)
    )
    return result.scalar_one_or_none()


async def count_all_requests(session: AsyncSession) -> int:
    """Подсчитывает общее количество всех заявок."""
    result = await session.execute(
        select(func.count(AbsenceRequest.id))
    )
    return result.scalar() or 0


async def count_pending_requests(session: AsyncSession) -> int:
    """Подсчитывает количество ожидающих заявок."""
    result = await session.execute(
        select(func.count(AbsenceRequest.id))
        .where(AbsenceRequest.status == RequestStatusEnum.PENDING.value)
    )
    return result.scalar() or 0


async def get_pending_requests_paginated(
    session: AsyncSession,
    offset: int = 0,
    limit: int = 1
) -> list[AbsenceRequest]:
    """Получает ожидающие заявки с пагинацией."""
    result = await session.execute(
        select(AbsenceRequest)
        .options(selectinload(AbsenceRequest.employee))
        .where(AbsenceRequest.status == RequestStatusEnum.PENDING.value)
        .order_by(AbsenceRequest.created_at.asc())
        .offset(offset)
        .limit(limit)
    )
    return list(result.scalars().all())


async def update_request_status(
    session: AsyncSession,
    request_id: int,
    new_status: Literal["approved", "rejected", "cancelled"],
    changed_by_id: int,
    reason: str | None = None
) -> AbsenceRequest | None:
    """Обновляет статус заявки и записывает в историю."""
    request = await get_request_by_id(session, request_id)
    if not request:
        return None

    old_status = request.status
    request.status = new_status

    if new_status == RequestStatusEnum.REJECTED.value and reason:
        request.rejected_reason = reason

    history = AbsenceRequestHistory(
        request_id=request_id,
        changed_by=changed_by_id,
        change_type=ChangeTypeEnum.STATUS_CHANGED.value,
        old_value=old_status,
        new_value=new_status,
        reason=reason
    )
    session.add(history)
    await session.commit()

    return request


async def get_user_requests_paginated(
    session: AsyncSession,
    employee_id: int,
    offset: int = 0,
    limit: int = 1
) -> list[AbsenceRequest]:
    """Получает заявки пользователя с пагинацией."""
    result = await session.execute(
        select(AbsenceRequest)
        .where(AbsenceRequest.employee_id == employee_id)
        .order_by(AbsenceRequest.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    return list(result.scalars().all())


async def count_user_requests(
    session: AsyncSession,
    employee_id: int
) -> int:
    """Подсчитывает количество заявок пользователя."""
    result = await session.execute(
        select(func.count(AbsenceRequest.id))
        .where(AbsenceRequest.employee_id == employee_id)
    )
    return result.scalar() or 0


async def cancel_request_by_user(
    session: AsyncSession,
    request_id: int,
    employee_id: int
) -> AbsenceRequest | None:
    """Отменяет заявку пользователем."""
    result = await session.execute(
        select(AbsenceRequest)
        .where(
            AbsenceRequest.id == request_id,
            AbsenceRequest.employee_id == employee_id
        )
    )
    request = result.scalar_one_or_none()

    if not request:
        return None

    if request.status != RequestStatusEnum.PENDING.value:
        return None

    request.status = RequestStatusEnum.CANCELLED.value

    history = AbsenceRequestHistory(
        request_id=request_id,
        changed_by=employee_id,
        change_type=ChangeTypeEnum.CANCELLED.value,
        old_value=RequestStatusEnum.PENDING.value,
        new_value=RequestStatusEnum.CANCELLED.value,
        reason="Отменено пользователем"
    )
    session.add(history)
    await session.commit()

    return request


async def get_all_requests_paginated(
    session: AsyncSession,
    offset: int = 0,
    limit: int = 5
) -> list[AbsenceRequest]:
    """Получает все заявки с пагинацией."""
    result = await session.execute(
        select(AbsenceRequest)
        .options(selectinload(AbsenceRequest.employee))
        .order_by(AbsenceRequest.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    return list(result.scalars().all())
