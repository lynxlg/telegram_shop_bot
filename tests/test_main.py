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
    start_webhook_server = AsyncMock(return_value="runner")
    stop_webhook_server = AsyncMock()

    monkeypatch.setattr(main_module, "create_bot", lambda: fake_bot)
    monkeypatch.setattr(main_module, "create_dispatcher", lambda: fake_dispatcher)
    monkeypatch.setattr(main_module, "init_db", init_db)
    monkeypatch.setattr(main_module, "dispose_engine", dispose_engine)
    monkeypatch.setattr(main_module, "start_yookassa_webhook_server", start_webhook_server)
    monkeypatch.setattr(main_module, "stop_yookassa_webhook_server", stop_webhook_server)

    await main_module.main()

    fake_dispatcher.update.middleware.assert_called_once()
    assert fake_dispatcher.include_router.call_count == 7
    fake_dispatcher.start_polling.assert_awaited_once_with(fake_bot)
    start_webhook_server.assert_awaited_once_with(fake_bot)
    stop_webhook_server.assert_awaited_once_with("runner")
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
    start_webhook_server = AsyncMock(return_value="runner")
    stop_webhook_server = AsyncMock()

    monkeypatch.setattr(main_module, "create_bot", lambda: fake_bot)
    monkeypatch.setattr(main_module, "create_dispatcher", lambda: fake_dispatcher)
    monkeypatch.setattr(main_module, "init_db", init_db)
    monkeypatch.setattr(main_module, "dispose_engine", dispose_engine)
    monkeypatch.setattr(main_module, "start_yookassa_webhook_server", start_webhook_server)
    monkeypatch.setattr(main_module, "stop_yookassa_webhook_server", stop_webhook_server)

    with pytest.raises(RuntimeError):
        await main_module.main()

    stop_webhook_server.assert_awaited_once_with("runner")
    fake_bot.session.close.assert_awaited_once()
    dispose_engine.assert_awaited_once()
