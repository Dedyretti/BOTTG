from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import AdminNotification


async def create_admin_notification(
    session: AsyncSession,
    request_id: int,
    admin_id: int,
    message_id: int,
    chat_id: int
) -> AdminNotification:
    """Создать запись об уведомлении админа."""

    notification = AdminNotification(
        request_id=request_id,
        admin_id=admin_id,
        message_id=message_id,
        chat_id=chat_id,
        is_active=True
    )
    session.add(notification)
    await session.flush()

    return notification


async def get_active_notifications_for_request(
    session: AsyncSession,
    request_id: int,
    exclude_admin_id: int | None = None
) -> list[AdminNotification]:
    """Получить все активные уведомления для заявки."""

    query = select(AdminNotification).where(
        AdminNotification.request_id == request_id,
        AdminNotification.is_active.is_(True)
    )

    if exclude_admin_id:
        query = query.where(AdminNotification.admin_id != exclude_admin_id)

    result = await session.execute(query)
    return list(result.scalars().all())


async def deactivate_notifications_for_request(
    session: AsyncSession,
    request_id: int,
    exclude_admin_id: int | None = None
) -> None:
    """Деактивировать уведомления для заявки."""

    query = (
        update(AdminNotification)
        .where(
            AdminNotification.request_id == request_id,
            AdminNotification.is_active.is_(True)
        )
        .values(is_active=False)
    )

    if exclude_admin_id:
        query = query.where(AdminNotification.admin_id != exclude_admin_id)

    await session.execute(query)
    await session.flush()
