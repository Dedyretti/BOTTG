# scripts/create_admin.py
import os
import sys
from pathlib import Path
import secrets
from datetime import datetime, timedelta, timezone

# Добавляем корень проекта в sys.path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy.orm import Session

from database.models import Employee, InviteCode
from database.db import SessionLocal


def validate_email(email: str) -> bool:
    import re

    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, email))


def validate_telegram_id(tg_id: str) -> bool:
    try:
        return int(tg_id) > 0
    except ValueError:
        return False


def generate_invite_code() -> str:
    """Генерирует уникальный инвайт-код."""
    return secrets.token_urlsafe(16)


def get_user_data():
    email = input("Введите почту: ")
    if not validate_email(email):
        print("❌ Неверный формат email")
        return None

    telegram_id = input("Введите Telegram ID (или Enter для пропуска): ")
    if telegram_id and not validate_telegram_id(telegram_id):
        print("❌ Неверный Telegram ID")
        return None

    return {
        "email": email,
        "telegram_id": int(telegram_id) if telegram_id else None,
        "name": input("Введите имя: "),
        "last_name": input("Введите фамилию: "),
    }


def create_invite_code_for_user(db: Session, employee: Employee) -> InviteCode:
    """Создает инвайт-код для сотрудника."""

    # Проверяем, есть ли уже активный инвайт
    existing_invite = (
        db.query(InviteCode)
        .filter(
            InviteCode.employee_id == employee.id,
            InviteCode.is_used == False,
            InviteCode.expires_at > datetime.now(timezone.utc),
        )
        .first()
    )

    if existing_invite:
        print(f"⚠️  У пользователя уже есть активный инвайт-код")
        return existing_invite

    # Создаем новый инвайт-код
    invite_code = InviteCode(
        code=generate_invite_code(),
        employee_id=employee.id,
        created_by=employee.id,  # Сам себя создал
        expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
        is_used=False,
    )

    db.add(invite_code)
    db.commit()
    db.refresh(invite_code)

    return invite_code


def create_or_update_superuser(db: Session, user_data: dict):
    existing_user = (
        db.query(Employee).filter(Employee.email == user_data["email"]).first()
    )

    if existing_user:
        print(f"✓ Найден: {existing_user.email}")

        existing_user.role = "superuser"
        existing_user.is_active = True
        existing_user.telegram_id = user_data.get("telegram_id")
        existing_user.name = user_data["name"]
        existing_user.last_name = user_data["last_name"]

        db.commit()
        print(f"✓ {existing_user.email} обновлен до суперпользователя")
        return existing_user
    else:
        new_superuser = Employee(
            email=user_data["email"],
            telegram_id=user_data.get("telegram_id"),
            name=user_data["name"],
            last_name=user_data["last_name"],
            role="superuser",
            is_active=True,
            position="Суперпользователь системы",
        )
        db.add(new_superuser)
        db.commit()
        db.refresh(new_superuser)

        print(f"✓ Создан новый суперпользователь: {new_superuser.email}")
        return new_superuser


def main():
    print("=" * 60)
    print(" " * 15 + "СОЗДАНИЕ СУПЕРПОЛЬЗОВАТЕЛЯ")
    print("=" * 60 + "\n")

    user_data = get_user_data()
    if not user_data:
        return

    db = SessionLocal()

    try:
        # Создаем/обновляем суперпользователя
        superuser = create_or_update_superuser(db, user_data)

        # Генерируем инвайт-код
        invite = create_invite_code_for_user(db, superuser)

        print("\n" + "=" * 60)
        print("✅ СУПЕРПОЛЬЗОВАТЕЛЬ УСПЕШНО СОЗДАН:")
        print("-" * 60)
        print(f"ID:           {superuser.id}")
        print(f"Email:        {superuser.email}")
        print(f"Telegram ID:  {superuser.telegram_id or 'Не указан'}")
        print(f"Имя:          {superuser.name} {superuser.last_name}")
        print(f"Роль:         {superuser.role}")
        print(f"Должность:    {superuser.position}")
        print("-" * 60)
        print("🔑 ИНВАЙТ-КОД ДЛЯ ПРИВЯЗКИ TELEGRAM:")
        print(f"   {invite.code}")
        print(f"   Истекает:  {invite.expires_at.strftime('%d.%m.%Y %H:%M')}")
        print("=" * 60)

        print("\n💡 Отправьте этот код боту для привязки Telegram аккаунта")

    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        import traceback

        traceback.print_exc()
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    main()
