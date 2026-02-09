from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from database.models import Employee, InviteCode
from database.enums import RoleEnum
from schemas.employee import EmployeeCreate


async def create_employee(
    session: AsyncSession,
    employee_data: EmployeeCreate,
    role: RoleEnum = RoleEnum.USER,
    create_invite: bool = True,
) -> Employee:
    """Функция для создания нового сотрудника в базе данных."""

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

        await session.refresh(employee)
        if create_invite:
            await session.refresh(invite_code)
        return employee
    except IntegrityError:
        await session.rollback()
        raise ValueError("Ошибка при создании сотрудника")


async def get_employee_by_email(
    session: AsyncSession, email: str
) -> Employee | None:
    """Функция для получения сотрудника по email."""

    result = await session.execute(
        select(Employee).where(Employee.email == email)
    )
    return result.scalar_one_or_none()


async def get_employee_by_id(
    session: AsyncSession, employee_id: int
) -> Employee | None:
    result = await session.execute(
        select(Employee)
        .where(Employee.id == employee_id)
        .options(selectinload(Employee.invite_codes))
    )
    return result.scalar_one_or_none()


async def create_superuser(
    session: AsyncSession,
    employee_data: EmployeeCreate,
) -> Employee:
    """Функция для создания суперпользователя в базе данных."""

    return await create_employee(session, employee_data, RoleEnum.SUPERUSER)
