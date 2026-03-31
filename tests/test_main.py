from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app import main as main_module


@pytest.mark.asyncio
async def test_main_runs_polling(monkeypatch) -> None:
    fake_bot = SimpleNamespace(session=SimpleNamespace(close=AsyncMock()))
    fake_dispatcher = SimpleNamespace(
        update=SimpleNamespace(middleware=MagicMock()),
        include_router=MagicMock(),
        start_polling=AsyncMock(),
    )
    init_db = AsyncMock()
    dispose_engine = AsyncMock()

    monkeypatch.setattr(main_module, "create_bot", lambda: fake_bot)
    monkeypatch.setattr(main_module, "create_dispatcher", lambda: fake_dispatcher)
    monkeypatch.setattr(main_module, "init_db", init_db)
    monkeypatch.setattr(main_module, "dispose_engine", dispose_engine)

    await main_module.main()

    fake_dispatcher.update.middleware.assert_called_once()
    fake_dispatcher.include_router.assert_called_once()
    fake_dispatcher.start_polling.assert_awaited_once_with(fake_bot)
    fake_bot.session.close.assert_awaited_once()
    dispose_engine.assert_awaited_once()


@pytest.mark.asyncio
async def test_main_reraises_unexpected_errors(monkeypatch) -> None:
    fake_bot = SimpleNamespace(session=SimpleNamespace(close=AsyncMock()))
    fake_dispatcher = SimpleNamespace(
        update=SimpleNamespace(middleware=MagicMock()),
        include_router=MagicMock(),
        start_polling=AsyncMock(side_effect=RuntimeError("boom")),
    )
    init_db = AsyncMock()
    dispose_engine = AsyncMock()

    monkeypatch.setattr(main_module, "create_bot", lambda: fake_bot)
    monkeypatch.setattr(main_module, "create_dispatcher", lambda: fake_dispatcher)
    monkeypatch.setattr(main_module, "init_db", init_db)
    monkeypatch.setattr(main_module, "dispose_engine", dispose_engine)

    with pytest.raises(RuntimeError):
        await main_module.main()

    fake_bot.session.close.assert_awaited_once()
    dispose_engine.assert_awaited_once()
