from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.exc import SQLAlchemyError

from app.models import database as database_module


class FakeAsyncContextManager:
    def __init__(self, value) -> None:
        self.value = value

    async def __aenter__(self):
        return self.value

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None


@pytest.mark.asyncio
async def test_get_db_yields_session_and_closes_it(monkeypatch) -> None:
    session = SimpleNamespace(close=AsyncMock())

    monkeypatch.setattr(database_module, "async_session_factory", lambda: session)

    generator = database_module.get_db()
    yielded_session = await anext(generator)

    assert yielded_session is session

    await generator.aclose()

    session.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_init_db_creates_tables(monkeypatch) -> None:
    connection = SimpleNamespace(
        execute=AsyncMock(),
        run_sync=AsyncMock(),
    )
    fake_engine = SimpleNamespace(begin=lambda: FakeAsyncContextManager(connection))

    monkeypatch.setattr(database_module, "engine", fake_engine)

    await database_module.init_db()

    connection.execute.assert_awaited_once()
    connection.run_sync.assert_awaited_once()


@pytest.mark.asyncio
async def test_init_db_raises_on_error(monkeypatch) -> None:
    connection = SimpleNamespace(
        execute=AsyncMock(side_effect=SQLAlchemyError("boom")),
        run_sync=AsyncMock(),
    )
    fake_engine = SimpleNamespace(begin=lambda: FakeAsyncContextManager(connection))

    monkeypatch.setattr(database_module, "engine", fake_engine)

    with pytest.raises(SQLAlchemyError):
        await database_module.init_db()


@pytest.mark.asyncio
async def test_dispose_engine_calls_dispose(monkeypatch) -> None:
    fake_engine = SimpleNamespace(dispose=AsyncMock())

    monkeypatch.setattr(database_module, "engine", fake_engine)

    await database_module.dispose_engine()

    fake_engine.dispose.assert_awaited_once()


@pytest.mark.asyncio
async def test_dispose_engine_raises_on_error(monkeypatch) -> None:
    fake_engine = SimpleNamespace(dispose=AsyncMock(side_effect=SQLAlchemyError("boom")))

    monkeypatch.setattr(database_module, "engine", fake_engine)

    with pytest.raises(SQLAlchemyError):
        await database_module.dispose_engine()
