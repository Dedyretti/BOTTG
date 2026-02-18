from aiogram.filters import BaseFilter
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from database.crud.employee import get_employee_by_telegram_id


async def is_user_verified(
    session: AsyncSession,
    telegram_id: int,
) -> bool:
    """Проверить, верифицирован ли пользователь (есть в БД)."""
    employee = await get_employee_by_telegram_id(session, telegram_id)
    return employee is not None


async def is_user_admin(
    session: AsyncSession,
    telegram_id: int,
) -> bool:
    """Проверить, является ли пользователь админом."""
    employee = await get_employee_by_telegram_id(session, telegram_id)

    if not employee:
        return False

    return employee.role in ("admin", "superuser")


async def get_user_role(
    session: AsyncSession,
    telegram_id: int,
) -> str | None:
    """Получить роль пользователя. None если не найден."""
    employee = await get_employee_by_telegram_id(session, telegram_id)

    if not employee:
        return None

    return employee.role


class IsVerifiedUser(BaseFilter):
    """Фильтр: пользователь верифицирован (есть в БД по telegram_id)."""

    async def __call__(
        self,
        event: Message | CallbackQuery,
        session: AsyncSession
    ) -> bool:
        return await is_user_verified(session, event.from_user.id)


class IsAdmin(BaseFilter):
    """Фильтр: пользователь — админ или суперюзер."""

    async def __call__(
        self,
        event: Message | CallbackQuery,
        session: AsyncSession
    ) -> bool:
        return await is_user_admin(session, event.from_user.id)


class IsAnonymous(BaseFilter):
    """Фильтр: пользователь НЕ верифицирован (нет в БД)."""

    async def __call__(
        self,
        event: Message | CallbackQuery,
        session: AsyncSession
    ) -> bool:
        return not await is_user_verified(session, event.from_user.id)
