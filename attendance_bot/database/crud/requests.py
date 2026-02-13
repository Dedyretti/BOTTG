from datetime import date
from typing import Literal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database.crud.employee import get_employee_by_telegram_id
from database.enums import ChangeTypeEnum, RequestStatusEnum
from database.models import AbsenceRequest, AbsenceRequestHistory


async def get_requests(session: AsyncSession) -> list[AbsenceRequest]:
    """Получить все ожидающие заявки."""

    result = await session.execute(
        select(AbsenceRequest)
        .where(AbsenceRequest.status == RequestStatusEnum.PENDING.value)
        .order_by(AbsenceRequest.created_at.desc())
    )
    return list(result.scalars().all())


async def count_requests(session: AsyncSession) -> int:
    """Подсчитать общее количество заявок."""

    result = await session.execute(
        select(func.count(AbsenceRequest.id))
    )
    return result.scalar()


async def count_pending_requests(session: AsyncSession) -> int:
    """Подсчитать количество ожидающих заявок."""

    result = await session.execute(
        select(func.count(AbsenceRequest.id))
        .where(AbsenceRequest.status == RequestStatusEnum.PENDING.value)
    )
    return result.scalar()


async def create_absence_request(
    session: AsyncSession,
    telegram_id: int,
    request_type: str,
    start_date: date,
    end_date: date,
    comment: str | None = None,
) -> AbsenceRequest | None:
    """Создаёт заявку на отсутствие и записывает в историю."""

    employee = await get_employee_by_telegram_id(session, telegram_id)
    if not employee:
        return None

    request = AbsenceRequest(
        employee_id=employee.id,
        request_type=request_type,
        start_date=start_date,
        end_date=end_date,
        comment=comment,
        status=RequestStatusEnum.PENDING.value
    )
    session.add(request)
    await session.flush()

    history = AbsenceRequestHistory(
        request_id=request.id,
        changed_by=employee.id,
        change_type=ChangeTypeEnum.CREATED.value,
        new_value=RequestStatusEnum.PENDING.value,
        reason="Заявка создана"
    )
    session.add(history)
    await session.commit()

    return request


async def get_request_by_id(
    session: AsyncSession,
    request_id: int
) -> AbsenceRequest | None:
    """Получить заявку по ID с данными сотрудника."""

    result = await session.execute(
        select(AbsenceRequest)
        .options(selectinload(AbsenceRequest.employee))
        .where(AbsenceRequest.id == request_id)
    )
    return result.scalar_one_or_none()


async def get_pending_requests_paginated(
    session: AsyncSession,
    offset: int = 0,
    limit: int = 1
) -> list[AbsenceRequest]:
    """Получить ожидающие заявки с пагинацией."""

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
    """Обновить статус заявки и записать в историю."""

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


async def cancel_user_request(
    session: AsyncSession,
    request_id: int,
    user_id: int
) -> AbsenceRequest | None:
    """Отменить заявку пользователем."""

    request = await get_request_by_id(session, request_id)
    if not request:
        return None

    employee = await get_employee_by_telegram_id(session, user_id)
    if not employee or request.employee_id != employee.id:
        return None

    if request.status != RequestStatusEnum.PENDING.value:
        return None

    request.status = RequestStatusEnum.CANCELLED.value

    history = AbsenceRequestHistory(
        request_id=request_id,
        changed_by=employee.id,
        change_type=ChangeTypeEnum.CANCELLED.value,
        old_value=RequestStatusEnum.PENDING.value,
        new_value=RequestStatusEnum.CANCELLED.value,
        reason="Отменено пользователем"
    )
    session.add(history)
    await session.commit()

    return request


async def get_user_pending_requests(
    session: AsyncSession,
    telegram_id: int,
    offset: int = 0,
    limit: int = 1
) -> list[AbsenceRequest]:
    """Получить ожидающие заявки пользователя с пагинацией."""

    employee = await get_employee_by_telegram_id(session, telegram_id)
    if not employee:
        return []

    result = await session.execute(
        select(AbsenceRequest)
        .where(
            AbsenceRequest.employee_id == employee.id,
            AbsenceRequest.status == RequestStatusEnum.PENDING.value
        )
        .order_by(AbsenceRequest.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    return list(result.scalars().all())


async def count_user_pending_requests(
    session: AsyncSession,
    telegram_id: int
) -> int:
    """Подсчитать количество ожидающих заявок пользователя."""

    employee = await get_employee_by_telegram_id(session, telegram_id)
    if not employee:
        return 0

    result = await session.execute(
        select(func.count(AbsenceRequest.id))
        .where(
            AbsenceRequest.employee_id == employee.id,
            AbsenceRequest.status == RequestStatusEnum.PENDING.value
        )
    )
    return result.scalar() or 0
