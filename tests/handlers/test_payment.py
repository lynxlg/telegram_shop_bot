from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.callbacks.payment import RETRY_PAYMENT_ACTION, PaymentCallback
from app.handlers import payment as payment_module
from app.handlers.payment import retry_payment


@pytest.mark.asyncio
async def test_retry_payment_updates_message_with_payment_link(
    callback_factory, monkeypatch
) -> None:
    callback = callback_factory()
    callback.from_user = SimpleNamespace(id=771111)

    async def fake_retry_payment_for_order(_db, *, order_id: int, telegram_id: int):
        assert order_id == 5
        assert telegram_id == 771111
        return SimpleNamespace(confirmation_url="https://pay.example/retry-5")

    monkeypatch.setattr(payment_module, "retry_payment_for_order", fake_retry_payment_for_order)

    await retry_payment(
        callback,
        PaymentCallback(action=RETRY_PAYMENT_ACTION, order_id=5),
        AsyncMock(),
    )

    callback.message.edit_text.assert_awaited_once()
    assert "Ссылка на оплату для заказа #5 готова." in callback.message.edit_text.await_args.args[0]


@pytest.mark.asyncio
async def test_retry_payment_shows_alert_when_order_missing(callback_factory, monkeypatch) -> None:
    callback = callback_factory()
    callback.from_user = SimpleNamespace(id=771112)

    async def fake_retry_payment_for_order(_db, *, order_id: int, telegram_id: int):
        raise payment_module.PaymentAttemptNotFoundError("missing")

    monkeypatch.setattr(payment_module, "retry_payment_for_order", fake_retry_payment_for_order)

    await retry_payment(
        callback,
        PaymentCallback(action=RETRY_PAYMENT_ACTION, order_id=9),
        AsyncMock(),
    )

    callback.answer.assert_awaited_once_with("Заказ не найден.", show_alert=True)
