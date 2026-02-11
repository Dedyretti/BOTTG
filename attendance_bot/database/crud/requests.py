from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import AbsenceRequest
from database.enums import RequestStatusEnum


async def get_requests(session: AsyncSession) -> list:
    result = await session.execute(
        select(AbsenceRequest)
        .where(AbsenceRequest.status == RequestStatusEnum.PENDING.value)
        .order_by(AbsenceRequest.created_at.desc())
    )
    return result.scalars().all()


async def count_requests(session: AsyncSession) -> int:
    result = await session.execute(
        select(func.count(AbsenceRequest.id))
    )
    return result.scalar()
