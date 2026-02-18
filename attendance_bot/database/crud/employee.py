from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from consts import INVITE_EXPIRE_HOURS
from database.enums import RoleEnum
from database.models import AbsenceRequest, Employee, InviteCode
from schemas.employee import EmployeeCreate


async def create_employee(
    session: AsyncSession,
    employee_data: EmployeeCreate,
    role: RoleEnum = RoleEnum.USER,
    create_invite: bool = True,
    invite_expire_hours: int = INVITE_EXPIRE_HOURS,
) -> Employee:
    """Создаёт нового сотрудника."""
    existing = await get_employee_by_email(session, employee_data.email)
    if existing:
        raise ValueError(
            f"Сотрудник с email {employee_data.email} уже существует"
        )

    employee = Employee(
        name=employee_data.name,
        last_name=employee_data.last_name,
        patronymic=employee_data.patronymic,
        email=employee_data.email,
        position=employee_data.position,
        role=role.value,
        is_active=True,
    )

    session.add(employee)
    await session.flush()

    if create_invite:
        expires_at = datetime.now(timezone.utc) + timedelta(
            hours=invite_expire_hours
        )
        invite_code = InviteCode(
            employee_id=employee.id,
            created_by=employee.id,
            expires_at=expires_at,
        )
        session.add(invite_code)

    try:
        await session.commit()
        await session.refresh(employee, ["invite_codes"])
        return employee
    except IntegrityError:
        await session.rollback()
        raise ValueError("Ошибка при создании сотрудника")


async def get_employee_by_email(
    session: AsyncSession,
    email: str
) -> Employee | None:
    """Получает сотрудника по email."""
    result = await session.execute(
        select(Employee).where(Employee.email == email)
    )
    return result.scalar_one_or_none()


async def get_employee_by_id(
    session: AsyncSession,
    employee_id: int
) -> Employee | None:
    """Получает сотрудника по ID с инвайт-кодами."""
    result = await session.execute(
        select(Employee)
        .where(Employee.id == employee_id)
        .options(selectinload(Employee.invite_codes))
    )
    return result.scalar_one_or_none()


async def get_employee_by_telegram_id(
    session: AsyncSession,
    telegram_id: int
) -> Employee | None:
    """Получает сотрудника по telegram_id."""
    result = await session.execute(
        select(Employee).where(Employee.telegram_id == telegram_id)
    )
    return result.scalar_one_or_none()


async def list_employees(session: AsyncSession) -> list[Employee]:
    """Получает всех сотрудников."""
    result = await session.execute(
        select(Employee).order_by(Employee.last_name, Employee.name)
    )
    return list(result.scalars().all())


async def count_employees(session: AsyncSession) -> int:
    """Подсчитывает общее количество сотрудников."""
    result = await session.execute(
        select(func.count(Employee.id))
    )
    return result.scalar() or 0


async def bind_telegram_to_employee(
    session: AsyncSession,
    employee_id: int,
    telegram_id: int,
) -> None:
    """Привязывает telegram_id к сотруднику."""
    await session.execute(
        update(Employee)
        .where(Employee.id == employee_id)
        .values(telegram_id=telegram_id)
    )
    await session.flush()


async def delete_employee_by_id(
    session: AsyncSession,
    employee_id: int
) -> Employee | None:
    """Удаляет сотрудника по ID."""
    employee = await session.get(Employee, employee_id)

    if not employee:
        return None

    deleted = Employee(
        id=employee.id,
        name=employee.name,
        last_name=employee.last_name,
        email=employee.email
    )

    await session.delete(employee)
    await session.commit()

    return deleted


async def get_employee_role(
    session: AsyncSession,
    telegram_id: int,
) -> str | None:
    """Получает роль пользователя."""
    employee = await get_employee_by_telegram_id(session, telegram_id)
    if not employee:
        return None
    return employee.role


async def get_admin_telegram_ids(session: AsyncSession) -> list[int]:
    """Получает telegram_id всех активных администраторов."""
    result = await session.execute(
        select(Employee.telegram_id).where(
            Employee.role.in_(["admin", "superuser"]),
            Employee.telegram_id.isnot(None),
            Employee.is_active.is_(True)
        )
    )
    return list(result.scalars().all())


async def get_employee_requests_count(
    session: AsyncSession,
    employee_id: int
) -> int:
    """Получает количество заявок сотрудника."""
    result = await session.execute(
        select(func.count(AbsenceRequest.id))
        .where(AbsenceRequest.employee_id == employee_id)
    )
    return result.scalar() or 0
