"""
CRUD операции для работы с сотрудниками.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from database.models import Employee
from database.enums import RoleEnum
from schemas.employee import EmployeeCreate


async def create_employee(
    session: AsyncSession,
    employee_data: EmployeeCreate,
    role: RoleEnum = RoleEnum.USER
) -> Employee:
    """
    Создает нового сотрудника.
    
    Args:
        session: Асинхронная сессия SQLAlchemy
        employee_data: Валидированные данные сотрудника
        role: Роль сотрудника (по умолчанию USER)
    
    Returns:
        Созданный объект Employee
        
    Raises:
        ValueError: Если сотрудник с таким email уже существует
    """
    existing_employee = await get_employee_by_email(session, employee_data.email)
    if existing_employee:
        raise ValueError(f"Сотрудник с email {employee_data.email} уже существует")
    
    employee = Employee(
        name=employee_data.name,
        last_name=employee_data.last_name,
        patronymic=employee_data.patronymic,
        email=employee_data.email,
        position=employee_data.position,
        role=role.value,  
        is_active=True
    )
    
    session.add(employee)
    
    try:
        await session.commit()
        await session.refresh(employee)
        return employee
    except IntegrityError:
        await session.rollback()
        raise ValueError("Ошибка при создании сотрудника")


async def get_employee_by_email(session: AsyncSession, email: str) -> Employee | None:
    """
    Находит сотрудника по email.
    
    Args:
        session: Асинхронная сессия SQLAlchemy
        email: Email сотрудника
        
    Returns:
        Объект Employee или None если не найден
    """
    result = await session.execute(
        select(Employee).where(Employee.email == email)
    )
    return result.scalar_one_or_none()


async def get_employee_by_id(session: AsyncSession, employee_id: int) -> Employee | None:
    """
    Находит сотрудника по ID.
    
    Args:
        session: Асинхронная сессия SQLAlchemy
        employee_id: ID сотрудника
        
    Returns:
        Объект Employee или None если не найден
    """
    result = await session.execute(
        select(Employee).where(Employee.id == employee_id)
    )
    return result.scalar_one_or_none()


async def create_superuser(
    session: AsyncSession,
    employee_data: EmployeeCreate
) -> Employee:
    """
    Создает суперпользователя.
    
    Args:
        session: Асинхронная сессия SQLAlchemy
        employee_data: Валидированные данные сотрудника
        
    Returns:
        Созданный объект Employee с ролью SUPERUSER
    """
    return await create_employee(session, employee_data, RoleEnum.SUPERUSER)