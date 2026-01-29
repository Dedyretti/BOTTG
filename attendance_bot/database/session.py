from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from config import config
from typing import AsyncGenerator



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

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
            
async def init_db():
    from models import Base
    
    async with engine.begin() as conn:
        # Создаем все таблицы
        await conn.run_sync(Base.metadata.create_all)
    
    print("База данных инициализирована")
