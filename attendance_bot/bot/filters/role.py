from aiogram.filters import BaseFilter
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from database.crud.verification_filter import is_user_admin, is_user_verified


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
        is_verified = await is_user_verified(session, event.from_user.id)
        return not is_verified
