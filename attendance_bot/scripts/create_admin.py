import asyncio
import sys
from pathlib import Path

current_dir = Path(__file__).parent
project_root = current_dir.parent
sys.path.insert(0, str(project_root))

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from config import config
from database.models import Base
from schemas.employee import EmployeeCreate
from crud.employee import create_superuser



async def init_db():
    """Инициализирует базу данных."""
    engine = create_async_engine(
        config.db.database_url,
        future=True,
    )
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    print("База данных инициализирована")
    return engine


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
    print("\n" + "="*50)
    print("Создание суперпользователя".center(50))
    print("="*50)

    engine = await init_db()

    AsyncSessionLocal = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    
    raw_data = collect_user_data()
    
    try:
        # Валидируем через Pydantic
        employee_schema = EmployeeCreate(**raw_data)
        
        # Создаем сессию и суперпользователя
        async with AsyncSessionLocal() as session:
            superuser = await create_superuser(session, employee_schema)
            
            print("\n Суперпользователь успешно создан!")
            print(f"   ID: {superuser.id}")
            print(f"   Имя: {superuser.name} {superuser.last_name}")
            print(f"   Email: {superuser.email}")
            print(f"   Роль: {superuser.role}")
            print(f"   Активен: {'Да' if superuser.is_active else 'Нет'}")
            
    except ValueError as e:
        print(f"\n❌ Ошибка валидации: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Неожиданная ошибка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())