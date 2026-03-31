import logging
from typing import AsyncGenerator, Optional

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings


logger = logging.getLogger(__name__)
settings = get_settings()


class Base(DeclarativeBase):
    pass


engine: AsyncEngine = create_async_engine(
    settings.database_url,
    echo=False,
    future=True,
)

async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    session: Optional[AsyncSession] = None

    try:
        session = async_session_factory()
        yield session
    except SQLAlchemyError:
        logger.exception("Database session error")
        raise
    finally:
        if session is not None:
            await session.close()


async def init_db() -> None:
    try:
        import app.models.user  # noqa: F401

        async with engine.begin() as connection:
            await connection.execute(text("SELECT 1"))
            await connection.run_sync(Base.metadata.create_all)

        logger.info("Database connection check and schema initialization completed")
    except SQLAlchemyError:
        logger.exception("Failed to initialize database")
        raise


async def dispose_engine() -> None:
    try:
        await engine.dispose()
        logger.info("Database engine disposed")
    except SQLAlchemyError:
        logger.exception("Failed to dispose database engine")
        raise
