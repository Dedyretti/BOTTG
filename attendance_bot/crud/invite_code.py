from datetime import datetime, timezone
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import InviteCode



async def create_invite_code(
    session: AsyncSession,
    employee_id: int,
    created_by: int | None = None
) -> InviteCode:
    """
    Создает новый инвайт-код.
    
    Args:
        session: Асинхронная сессия SQLAlchemy
        employee_id: ID сотрудника для привязки
        created_by: ID создателя (опционально)
        
    Returns:
        Созданный объект InviteCode
    """
    code = str(uuid.uuid4())[:8].upper()
    
    invite_code = InviteCode(
        code=code,
        employee_id=employee_id,
        created_by=created_by
    )
    
    session.add(invite_code)
    await session.commit()
    await session.refresh(invite_code)
    
    return invite_code


async def get_invite_code(session: AsyncSession, code: str) -> InviteCode | None:
    """
    Находит инвайт-код по коду.
    
    Args:
        session: Асинхронная сессия SQLAlchemy
        code: Код инвайта
        
    Returns:
        Объект InviteCode или None если не найден
    """
    result = await session.execute(
        select(InviteCode).where(InviteCode.code == code)
    )
    return result.scalar_one_or_none()


async def mark_invite_code_used(
    session: AsyncSession,
    code: str
) -> InviteCode | None:
    """
    Помечает инвайт-код как использованный.
    
    Args:
        session: Асинхронная сессия SQLAlchemy
        code: Код инвайта
        
    Returns:
        Обновленный объект InviteCode или None если не найден
    """
    invite_code = await get_invite_code(session, code)
    
    if invite_code and not invite_code.is_used:
        invite_code.is_used = True
        invite_code.used_at = datetime.now(timezone.utc)
        await session.commit()
        await session.refresh(invite_code)
    
    return invite_code