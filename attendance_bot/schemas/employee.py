from typing import Optional
from pydantic import BaseModel, EmailStr, field_validator, ConfigDict
from database.enums import RoleEnum


class EmployeeCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str
    last_name: str
    patronymic: Optional[str] = None
    email: EmailStr
    position: Optional[str] = None
    role: RoleEnum = RoleEnum.USER

    @field_validator('name', 'last_name')
    @classmethod
    def validate_name_length(cls, v: str) -> str:
        if len(v.strip()) < 2:
            raise ValueError('Должно быть не менее 2 символов')
        return v

    @field_validator('email')
    @classmethod
    def normalize_email(cls, v: str) -> str:
        return v.lower()
