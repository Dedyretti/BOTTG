from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from config import config


# Убрали get_db и connect_args
engine = create_async_engine(
    config.db.database_url,
    future=True,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def init_db():
    """Инициализация базы данных."""
    from database.models import Base
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    print("База данных инициализирована")