from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, field_validator

from database.enums import RoleEnum


class EmployeeCreate(BaseModel):
    """Схема для создания нового сотрудника."""

    model_config = ConfigDict(str_strip_whitespace=True)
    name: str
    last_name: str
    patronymic: None | str = None
    email: EmailStr
    position: None | str = None
    role: RoleEnum = RoleEnum.USER

    @field_validator("name", "last_name")
    @classmethod
    def validate_name_length(cls, v: str) -> str:
        if len(v.strip()) < 2:
            raise ValueError("Должно быть не менее 2 символов")
        return v

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        return v.lower()


class EmployeeUpdate(BaseModel):
    """Схема для обновления сотрудника."""

    model_config = ConfigDict(str_strip_whitespace=True)
    name: Optional[str] = None
    last_name: Optional[str] = None
    patronymic: Optional[str] = None
    position: Optional[str] = None
    role: Optional[RoleEnum] = None

    @field_validator("name", "last_name")
    @classmethod
    def validate_name_length(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and len(v.strip()) < 2:
            raise ValueError("Должно быть не менее 2 символов")
        return v
