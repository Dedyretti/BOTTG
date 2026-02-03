import uuid
from datetime import datetime, timedelta, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import InviteCode
from consts import INVITE_EXPIRE_HOURS


async def create_invite_code(
    session: AsyncSession,
    employee_id: int,
    created_by: int | None = None,
) -> InviteCode:
    code = str(uuid.uuid4())[:8].upper()

    expires_at = datetime.now(timezone.utc) + timedelta(
        hours=INVITE_EXPIRE_HOURS
    )

    invite_code = InviteCode(
        code=code,
        employee_id=employee_id,
        created_by=created_by,
        expires_at=expires_at,
    )

    session.add(invite_code)
    await session.commit()
    await session.refresh(invite_code)

    return invite_code


async def get_invite_code(
    session: AsyncSession, code: str
) -> InviteCode | None:
    result = await session.execute(
        select(InviteCode).where(InviteCode.code == code)
    )
    return result.scalar_one_or_none()


async def mark_invite_code_used(
    session: AsyncSession,
    code: str,
) -> InviteCode | None:
    invite_code = await get_invite_code(session, code)

    if invite_code and not invite_code.is_used:
        invite_code.is_used = True
        invite_code.used_at = datetime.now(timezone.utc)
        await session.commit()
        await session.refresh(invite_code)

    return invite_code


async def create_invite_code_with_custom_expiry(
    session: AsyncSession,
    employee_id: int,
    created_by: int | None = None,
    expire_hours: int = None,
) -> InviteCode:
    code = str(uuid.uuid4())[:8].upper()

    hours = expire_hours if expire_hours is not None else INVITE_EXPIRE_HOURS
    expires_at = datetime.now(timezone.utc) + timedelta(hours=hours)

    invite_code = InviteCode(
        code=code,
        employee_id=employee_id,
        created_by=created_by,
        expires_at=expires_at,
    )

    session.add(invite_code)
    await session.commit()
    await session.refresh(invite_code)

    return invite_code
