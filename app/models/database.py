import logging
from typing import AsyncGenerator, Optional

from sqlalchemy import text
from sqlalchemy.engine.url import make_url
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


def _build_admin_database_url(database_url: str) -> Optional[str]:
    sync_url = make_url(database_url.replace("+asyncpg", "", 1))

    if not sync_url.drivername.startswith("postgresql"):
        return None

    admin_url = (
        sync_url.set(database="postgres")
        .render_as_string(hide_password=False)
        .replace("postgresql://", "postgresql+asyncpg://", 1)
    )
    return admin_url


def _quote_identifier(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


async def ensure_database_exists() -> None:
    database_url = settings.database_url
    sync_url = make_url(database_url.replace("+asyncpg", "", 1))
    database_name = sync_url.database
    admin_database_url = _build_admin_database_url(database_url)

    if admin_database_url is None or database_name is None:
        return

    admin_engine = create_async_engine(
        admin_database_url,
        future=True,
        isolation_level="AUTOCOMMIT",
    )

    try:
        async with admin_engine.connect() as connection:
            result = await connection.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :database_name"),
                {"database_name": database_name},
            )
            database_exists = result.scalar_one_or_none() is not None

            if not database_exists:
                await connection.execute(
                    text(f"CREATE DATABASE {_quote_identifier(database_name)}")
                )
                logger.info("Database %s created", database_name)
    except SQLAlchemyError:
        logger.exception("Failed to ensure database exists")
        raise
    finally:
        await admin_engine.dispose()


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
        import app.models.category  # noqa: F401
        import app.models.product  # noqa: F401
        import app.models.product_attribute  # noqa: F401
        import app.models.user  # noqa: F401

        await ensure_database_exists()

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
