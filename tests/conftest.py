from pathlib import Path
from types import SimpleNamespace
from typing import AsyncGenerator, Callable, Optional
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

from app.handlers.catalog import router as catalog_router
from app.handlers.cart import router as cart_router
from app.handlers.common.start import router as start_router
from app.models.cart import Cart
from app.models.cart_item import CartItem
from app.models.category import Category
from app.models.database import Base
from app.models.product import Product
from app.models.product_attribute import ProductAttribute


TEST_ENV_FILE = Path(__file__).resolve().parent / ".env.test"
INTEGRATION_FIXTURES = {"db_session", "test_engine", "test_session_factory"}


def _to_sync_database_url(database_url: str) -> str:
    return database_url.replace("+asyncpg", "", 1)


def pytest_addoption(parser) -> None:
    parser.addoption(
        "--run-integration",
        action="store_true",
        default=False,
        help="run PostgreSQL integration tests",
    )


def pytest_collection_modifyitems(config, items) -> None:
    run_integration = config.getoption("--run-integration")
    skip_integration = pytest.mark.skip(
        reason="integration tests skipped; use --run-integration"
    )

    for item in items:
        fixture_names = set(getattr(item, "fixturenames", ()))
        if fixture_names & INTEGRATION_FIXTURES:
            item.add_marker(pytest.mark.integration)
        else:
            item.add_marker(pytest.mark.unit)

        if "integration" in item.keywords and not run_integration:
            item.add_marker(skip_integration)


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
            await connection.run_sync(Base.metadata.drop_all)
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
            await connection.execute(
                text(
                    "TRUNCATE TABLE "
                    "cart_items, carts, product_attributes, products, categories, users "
                    "RESTART IDENTITY CASCADE"
                )
            )


@pytest.fixture
def bot() -> Bot:
    return Bot(token="123456:TEST_TOKEN")


@pytest.fixture
def dp() -> Dispatcher:
    dispatcher = Dispatcher()
    dispatcher.include_router(start_router)
    dispatcher.include_router(catalog_router)
    dispatcher.include_router(cart_router)
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
def callback_factory() -> Callable[..., SimpleNamespace]:
    def factory(message: Optional[SimpleNamespace] = None) -> SimpleNamespace:
        async def answer(*args, **kwargs):
            return SimpleNamespace(args=args, kwargs=kwargs)

        callback_message = message or SimpleNamespace(
            edit_text=AsyncMock(side_effect=answer),
            edit_media=AsyncMock(side_effect=answer),
            answer=AsyncMock(side_effect=answer),
            delete=AsyncMock(side_effect=answer),
        )
        return SimpleNamespace(
            message=callback_message,
            answer=AsyncMock(side_effect=answer),
        )

    return factory


@pytest.fixture
def category_factory() -> Callable[..., Category]:
    def factory(name: str, parent_id: Optional[int] = None) -> Category:
        return Category(name=name, parent_id=parent_id)

    return factory


@pytest.fixture
def product_factory() -> Callable[..., Product]:
    def factory(
        category_id: int,
        name: str,
        price,
        description: Optional[str] = "Описание товара",
        image_url: Optional[str] = None,
        is_active: bool = True,
    ) -> Product:
        return Product(
            category_id=category_id,
            name=name,
            price=price,
            description=description,
            image_url=image_url,
            is_active=is_active,
        )

    return factory


@pytest.fixture
def product_attribute_factory() -> Callable[..., ProductAttribute]:
    def factory(product_id: int, name: str, value: str) -> ProductAttribute:
        return ProductAttribute(product_id=product_id, name=name, value=value)

    return factory


@pytest.fixture
def db_error() -> SQLAlchemyError:
    return SQLAlchemyError("database error")


@pytest.fixture
def cart_factory() -> Callable[..., Cart]:
    def factory(user_id: int) -> Cart:
        return Cart(user_id=user_id)

    return factory


@pytest.fixture
def cart_item_factory() -> Callable[..., CartItem]:
    def factory(cart_id: int, product_id: int, quantity: int = 1) -> CartItem:
        return CartItem(cart_id=cart_id, product_id=product_id, quantity=quantity)

    return factory
