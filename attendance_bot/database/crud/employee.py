from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from database.models import Employee, InviteCode
from database.enums import RoleEnum
from schemas.employee import EmployeeCreate


async def create_employee(
    session: AsyncSession,
    employee_data: EmployeeCreate,
    role: RoleEnum = RoleEnum.USER,
    create_invite: bool = True,
) -> Employee:
    """Создаёт нового сотрудника в базе данных."""

    existing_employee = await get_employee_by_email(
        session, employee_data.email
    )
    if existing_employee:
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
        invite_code = InviteCode(
            employee_id=employee.id,
            created_by=employee.id,
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


async def delete_employee(
    session: AsyncSession,
    employee: Employee
) -> None:
    """Удаляет сотрудника из базы данных."""

    await session.delete(employee)
    await session.commit()


async def create_superuser(
    session: AsyncSession,
    employee_data: EmployeeCreate,
) -> Employee:
    """Создаёт суперпользователя."""

    return await create_employee(session, employee_data, RoleEnum.SUPERUSER)


async def list_employees(session: AsyncSession) -> list[Employee]:
    """Получает всех сотрудников из базы данных."""

    result = await session.execute(
        select(Employee).order_by(
            Employee.id,
            Employee.last_name,
            Employee.name,
            Employee.position,
            Employee.role
        )
    )
    return result.scalars().all()


async def bind_telegram_to_employee(
    session: AsyncSession,
    employee_id: int,
    telegram_id: int,
) -> None:
    """Привязать telegram_id к сотруднику."""

    await session.execute(
        update(Employee)
        .where(Employee.id == employee_id)
        .values(telegram_id=telegram_id)
    )
    await session.flush()


async def get_employee_by_telegram_id(
    session: AsyncSession,
    telegram_id: int
) -> Employee | None:
    """Получает сотрудника по telegram_id."""

    result = await session.execute(
        select(Employee).where(Employee.telegram_id == telegram_id)
    )
    return result.scalar_one_or_none()
