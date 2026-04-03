from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session, sessionmaker

from leads.config import settings

# Engine assíncrono para uso no FastAPI
async_engine = create_async_engine(
    settings.database_url.replace("postgresql+psycopg://", "postgresql+psycopg://"),
    pool_size=10,
    max_overflow=20,
    echo=settings.log_level == "DEBUG",
)

AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# Engine síncrono para uso no Alembic e ingestão bulk
sync_engine = create_engine(
    settings.sync_database_url,
    pool_size=5,
    max_overflow=10,
    echo=settings.log_level == "DEBUG",
)

SyncSessionLocal = sessionmaker(bind=sync_engine, class_=Session, expire_on_commit=False)


async def get_async_session():
    """Dependency para FastAPI."""
    async with AsyncSessionLocal() as session:
        yield session


def get_sync_session():
    """Context manager síncrono para ingestão."""
    with SyncSessionLocal() as session:
        yield session
