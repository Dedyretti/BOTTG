import asyncio
import sys
from pathlib import Path

from sqlalchemy.exc import OperationalError

from crud.employee import create_superuser
from database.session import AsyncSessionLocal
from schemas.employee import EmployeeCreate

current_dir = Path(__file__).parent
project_root = current_dir.parent
sys.path.insert(0, str(project_root))


def collect_user_data() -> dict:
    """Собирает данные от пользователя."""
    print("\nВведите данные суперпользователя:")
    return {
        'name': input("Имя: "),
        'last_name': input("Фамилия: "),
        'patronymic': input("Отчество (опционально): ") or None,
        'email': input("Email: "),
        'position': input("Должность (опционально): ") or None,
    }


async def main():
    """Основная функция скрипта."""
    print("\n" + "=" * 50)
    print("Создание суперпользователя".center(50))
    print("=" * 50)
    raw_data = collect_user_data()
    try:
        employee_schema = EmployeeCreate(**raw_data)
        async with AsyncSessionLocal() as session:
            superuser = await create_superuser(session, employee_schema)
            print(" Суперпользователь успешно создан!")
            print(f"   ID: {superuser.id}")
            print(f"   Имя: {superuser.name} {superuser.last_name}")
            print(f"   Email: {superuser.email}")
            print(f"   Роль: {superuser.role}")
            print(f"   Активен: {'Да' if superuser.is_active else 'Нет'}")
    except OperationalError as e:
        print(f"\n❌ Ошибка базы данных: {e}")
        print("ℹ️  Возможно таблицы не созданы. Выполните миграции:")
        print("   alembic upgrade head")
        sys.exit(1)
    except ValueError as e:
        print(f"\n❌ Ошибка валидации: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Неожиданная ошибка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
