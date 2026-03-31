from pathlib import Path
from types import SimpleNamespace
from typing import AsyncGenerator, Callable
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from aiogram import Bot, Dispatcher
from sqlalchemy import text
from sqlalchemy.engine.url import make_url
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.handlers.common.start import router as start_router
from app.models.database import Base


TEST_ENV_FILE = Path(__file__).resolve().parent / ".env.test"


def _to_sync_database_url(database_url: str) -> str:
    return database_url.replace("+asyncpg", "", 1)

@pytest.fixture(scope="session")
def test_settings():
    from app.config import Settings

    return Settings(_env_file=TEST_ENV_FILE)


@pytest_asyncio.fixture
async def test_engine(test_settings) -> AsyncGenerator[AsyncEngine, None]:
    database_url = test_settings.database_url
    database_name = make_url(_to_sync_database_url(database_url)).database
    admin_database_url = (
        make_url(database_url.replace("+asyncpg", "", 1))
        .set(database="postgres")
        .render_as_string(hide_password=False)
        .replace("postgresql://", "postgresql+asyncpg://", 1)
    )
    admin_engine = create_async_engine(
        admin_database_url,
        future=True,
        isolation_level="AUTOCOMMIT",
    )

    try:
        async with admin_engine.connect() as connection:
            result = await connection.execute(
                text(
                    "SELECT 1 FROM pg_database WHERE datname = :database_name"
                ),
                {"database_name": database_name},
            )
            database_exists = result.scalar_one_or_none() is not None

            if not database_exists:
                await connection.execute(text(f'CREATE DATABASE "{database_name}"'))
    except Exception:
        await admin_engine.dispose()
        pytest.skip("Не удалось создать отдельную тестовую БД PostgreSQL")
    finally:
        await admin_engine.dispose()

    engine = create_async_engine(database_url, future=True)

    try:
        async with engine.begin() as connection:
            await connection.execute(text("SELECT 1"))
            await connection.run_sync(Base.metadata.create_all)
    except Exception:
        await engine.dispose()
        pytest.skip("PostgreSQL недоступен для интеграционных тестов")

    try:
        yield engine
    finally:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.drop_all)

        await engine.dispose()

        admin_engine = create_async_engine(
            admin_database_url,
            future=True,
            isolation_level="AUTOCOMMIT",
        )
        try:
            async with admin_engine.connect() as connection:
                await connection.execute(
                    text(
                        "SELECT pg_terminate_backend(pid) "
                        "FROM pg_stat_activity "
                        "WHERE datname = :database_name AND pid <> pg_backend_pid()"
                    ),
                    {"database_name": database_name},
                )
                await connection.execute(text(f'DROP DATABASE IF EXISTS "{database_name}"'))
        finally:
            await admin_engine.dispose()


@pytest.fixture
def test_session_factory(test_engine: AsyncEngine):
    return async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
        autocommit=False,
    )


@pytest_asyncio.fixture
async def db_session(test_engine: AsyncEngine, test_session_factory) -> AsyncGenerator[AsyncSession, None]:
    session = test_session_factory()

    try:
        yield session
    finally:
        await session.close()

        async with test_engine.begin() as connection:
            await connection.execute(text("TRUNCATE TABLE users RESTART IDENTITY CASCADE"))


@pytest.fixture
def bot() -> Bot:
    return Bot(token="123456:TEST_TOKEN")


@pytest.fixture
def dp() -> Dispatcher:
    dispatcher = Dispatcher()
    dispatcher.include_router(start_router)
    return dispatcher


@pytest.fixture
def message_factory() -> Callable[..., SimpleNamespace]:
    def factory(
        telegram_id: int = 123456789,
        username: str = "test_user",
        first_name: str = "Test",
        last_name: str = "User",
        text_value: str = "/start",
    ) -> SimpleNamespace:
        async def answer(*args, **kwargs):
            return SimpleNamespace(args=args, kwargs=kwargs)

        return SimpleNamespace(
            text=text_value,
            from_user=SimpleNamespace(
                id=telegram_id,
                username=username,
                first_name=first_name,
                last_name=last_name,
            ),
            answer=AsyncMock(side_effect=answer),
        )

    return factory


@pytest.fixture
def db_error() -> SQLAlchemyError:
    return SQLAlchemyError("database error")
