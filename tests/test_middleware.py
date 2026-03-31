from types import SimpleNamespace

import pytest
from sqlalchemy.exc import SQLAlchemyError

from app.middlewares.db_session import DbSessionMiddleware


class FakeSession:
    def __init__(self) -> None:
        self.closed = False

    async def close(self) -> None:
        self.closed = True


class FakeSessionContext:
    def __init__(self, session: FakeSession) -> None:
        self.session = session

    async def __aenter__(self) -> FakeSession:
        return self.session

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.session.close()


@pytest.mark.asyncio
async def test_middleware_adds_db_to_data(monkeypatch) -> None:
    middleware = DbSessionMiddleware()
    session = FakeSession()

    monkeypatch.setattr(
        "app.middlewares.db_session.async_session_factory",
        lambda: FakeSessionContext(session),
    )

    captured = {}

    async def handler(event, data):
        captured["db"] = data["db"]
        return "ok"

    result = await middleware(handler, SimpleNamespace(), {})

    assert result == "ok"
    assert captured["db"] is session


@pytest.mark.asyncio
async def test_middleware_closes_session_after_success(monkeypatch) -> None:
    middleware = DbSessionMiddleware()
    session = FakeSession()

    monkeypatch.setattr(
        "app.middlewares.db_session.async_session_factory",
        lambda: FakeSessionContext(session),
    )

    async def handler(event, data):
        return "done"

    await middleware(handler, SimpleNamespace(), {})

    assert session.closed is True


@pytest.mark.asyncio
async def test_middleware_closes_session_after_handler_error(monkeypatch) -> None:
    middleware = DbSessionMiddleware()
    session = FakeSession()

    monkeypatch.setattr(
        "app.middlewares.db_session.async_session_factory",
        lambda: FakeSessionContext(session),
    )

    async def handler(event, data):
        raise RuntimeError("handler error")

    with pytest.raises(RuntimeError):
        await middleware(handler, SimpleNamespace(), {})

    assert session.closed is True


@pytest.mark.asyncio
async def test_middleware_reraises_database_error(monkeypatch) -> None:
    middleware = DbSessionMiddleware()
    session = FakeSession()

    monkeypatch.setattr(
        "app.middlewares.db_session.async_session_factory",
        lambda: FakeSessionContext(session),
    )

    async def handler(event, data):
        raise SQLAlchemyError("db error")

    with pytest.raises(SQLAlchemyError):
        await middleware(handler, SimpleNamespace(), {})

    assert session.closed is True
