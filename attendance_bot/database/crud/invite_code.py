from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import InviteCode
from consts import INVITE_EXPIRE_HOURS


async def mark_invite_code_used(

    session: AsyncSession,
    code: str,
) -> InviteCode | None:
    """Функция для пометки инвайт-кода как использованного."""
    invite_code = await get_invite_code(session, code)

    if invite_code and not invite_code.is_used:
        invite_code.is_used = True
        invite_code.used_at = datetime.now(timezone.utc)
        await session.commit()
        await session.refresh(invite_code)

    return invite_code


async def get_invite_code(

    session: AsyncSession,
    employee_id: int,
    created_by: int | None = None,
    expire_hours: int = INVITE_EXPIRE_HOURS,
) -> InviteCode:
    """Функция для получения нового инвайт-кода для сотрудника."""

    expires_at = datetime.now(timezone.utc) + timedelta(hours=expire_hours)

    invite_code = InviteCode(
        employee_id=employee_id,
        created_by=created_by,
        expires_at=expires_at,
    )

    session.add(invite_code)
    await session.commit()
    await session.refresh(invite_code)

    return invite_code
