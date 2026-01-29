import asyncio
import sys
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config
from alembic import context

# Добавляем корень проекта в Python path
sys.path.append(str(Path(__file__).parent.parent))

# Импортируем наш конфиг и Base из моделей
from config import config
from database.models import Base  # или from models import Base, если модели в корне

# Наш target_metadata
target_metadata = Base.metadata

# Получаем URL базы данных из конфига
DATABASE_URL = str(config.db.database_url)

# Конфигурация Alembic
alembic_config = context.config

# Устанавливаем наш URL
alembic_config.set_main_option("sqlalchemy.url", DATABASE_URL)

# Настраиваем логирование
if alembic_config.config_file_name is not None:
    fileConfig(alembic_config.config_file_name)

def run_migrations_offline() -> None:
    """Запуск миграций в оффлайн режиме."""
    context.configure(
        url=DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()

def do_run_migrations(connection: Connection) -> None:
    """Запуск миграций с переданным соединением."""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
    )

    with context.begin_transaction():
        context.run_migrations()

async def run_async_migrations() -> None:
    """Асинхронный запуск миграций."""
    connectable = async_engine_from_config(
        alembic_config.get_section(alembic_config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()

def run_migrations_online() -> None:
    """Запуск миграций в онлайн режиме."""
    asyncio.run(run_async_migrations())

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()