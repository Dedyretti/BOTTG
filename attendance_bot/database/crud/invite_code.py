from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from consts import INVITE_EXPIRE_HOURS
from database.models import InviteCode


def _utc_now() -> datetime:
    """Возвращает текущее UTC время без timezone (naive)."""

    return datetime.utcnow()


def _make_naive(dt: datetime) -> datetime:
    """Убирает timezone из datetime, если есть."""

    if dt.tzinfo is not None:
        return dt.replace(tzinfo=None)
    return dt


def _to_uuid(code: str | UUID) -> UUID:
    """Преобразует строку в UUID, если нужно."""

    if isinstance(code, UUID):
        return code
    return UUID(code)


async def mark_invite_code_used(
    session: AsyncSession,
    code: str | UUID,
) -> InviteCode | None:
    """Функция для пометки инвайт-кода как использованного."""

    code_uuid = _to_uuid(code)
    invite_code = await get_invite_code_by_code(session, code_uuid)

    if invite_code and not invite_code.is_used:
        invite_code.is_used = True
        invite_code.used_at = _utc_now()
        await session.commit()
        await session.refresh(invite_code)

    return invite_code


async def get_invite_code_by_code(
    session: AsyncSession,
    code: str | UUID,
) -> InviteCode | None:
    """Получить инвайт-код по коду."""

    code_uuid = _to_uuid(code)

    result = await session.execute(
        select(InviteCode).where(InviteCode.code == code_uuid)
    )
    return result.scalar_one_or_none()


async def get_invite_code_for_employee(
    session: AsyncSession,
    employee_id: int,
    code: str | UUID,
) -> InviteCode | None:
    """
    Получить инвайт-код по UUID и employee_id.
    Без проверки is_used и expires_at — для детальной диагностики.
    """
    code_uuid = _to_uuid(code)

    result = await session.execute(
        select(InviteCode).where(
            InviteCode.employee_id == employee_id,
            InviteCode.code == code_uuid
        )
    )
    return result.scalar_one_or_none()


def check_invite_code_status(invite: InviteCode) -> str | None:
    """
    Проверяет статус инвайт-кода.

    Возвращает:
        - None если код валидный
        - "used" если код уже использован
        - "expired" если код просрочен
    """
    if invite.is_used:
        return "used"

    if invite.expires_at:
        expires_at = _make_naive(invite.expires_at)
        now = _utc_now()

        if expires_at < now:
            return "expired"

    return None


def format_invite_expiry(expires_at: datetime) -> str:
    """Форматирует дату истечения в читаемый вид."""

    if expires_at is None:
        return "не указано"
    return expires_at.strftime("%d.%m.%Y в %H:%M UTC")


async def get_active_invite_code(
    session: AsyncSession,
    employee_id: int,
) -> InviteCode | None:
    """Получить активный инвайт-код для сотрудника."""

    now = _utc_now()

    result = await session.execute(
        select(InviteCode).where(
            InviteCode.employee_id == employee_id,
            InviteCode.is_used.is_(False),
            InviteCode.expires_at > now
        )
    )
    return result.scalar_one_or_none()


async def deactivate_old_invite_codes(
    session: AsyncSession,
    employee_id: int,
) -> None:
    """Деактивировать все старые неиспользованные коды сотрудника."""

    result = await session.execute(
        select(InviteCode).where(
            InviteCode.employee_id == employee_id,
            InviteCode.is_used.is_(False),
        )
    )
    old_codes = result.scalars().all()
    for old_code in old_codes:
        old_code.is_used = True
    await session.flush()


async def create_invite_code(
    session: AsyncSession,
    employee_id: int,
    created_by: int | None = None,
    expire_hours: int = INVITE_EXPIRE_HOURS,
) -> InviteCode:
    """Создать новый инвайт-код для сотрудника."""

    expires_at = _utc_now() + timedelta(hours=expire_hours)

    invite_code = InviteCode(
        employee_id=employee_id,
        created_by=created_by,
        expires_at=expires_at,
    )

    session.add(invite_code)
    await session.flush()
    await session.refresh(invite_code)

    return invite_code
