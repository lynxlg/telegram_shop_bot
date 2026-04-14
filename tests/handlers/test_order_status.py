from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from sqlalchemy.exc import SQLAlchemyError

from app.handlers import order_status as order_status_module
from app.handlers.order_status import show_active_order_statuses
from app.models.order import Order
from app.models.user import User


@pytest.mark.asyncio
async def test_show_active_order_statuses_unit_happy_path(message_factory, monkeypatch) -> None:
    message = message_factory(text_value="Статус заказа")

    async def fake_get_active_orders(_db, _telegram_id):
        return [
            SimpleNamespace(order_number="ORD-900001", status="new"),
            SimpleNamespace(order_number="ORD-900002", status="assembling"),
        ]

    monkeypatch.setattr(
        order_status_module,
        "get_active_orders_by_telegram_id",
        fake_get_active_orders,
    )

    await show_active_order_statuses(message, AsyncMock())

    message.answer.assert_awaited_once_with(
        "Активные заказы:\n\n"
        "1. ORD-900001 - Принят\n"
        "2. ORD-900002 - Собран"
    )


@pytest.mark.asyncio
async def test_show_active_order_statuses_unit_empty_state(message_factory, monkeypatch) -> None:
    message = message_factory(text_value="Статус заказа")

    async def fake_get_active_orders(_db, _telegram_id):
        return []

    monkeypatch.setattr(
        order_status_module,
        "get_active_orders_by_telegram_id",
        fake_get_active_orders,
    )

    await show_active_order_statuses(message, AsyncMock())

    message.answer.assert_awaited_once_with("У вас нет активных заказов.")


@pytest.mark.asyncio
async def test_show_active_order_statuses_lists_only_current_user_active_orders(
    db_session,
    message_factory,
) -> None:
    user = User(telegram_id=551001, username="buyer", first_name="Buyer", last_name="One")
    other_user = User(telegram_id=551002, username="other", first_name="Other", last_name="User")
    db_session.add_all([user, other_user])
    await db_session.flush()
    db_session.add_all(
        [
            Order(
                user_id=user.id,
                order_number="ORD-000001",
                status="new",
                phone="+79990000001",
                shipping_address="Москва, Арбат 1",
                total_amount="100.00",
                created_at=datetime.now(timezone.utc),
            ),
            Order(
                user_id=user.id,
                order_number="ORD-000002",
                status="delivering",
                phone="+79990000001",
                shipping_address="Москва, Арбат 1",
                total_amount="150.00",
                created_at=datetime.now(timezone.utc),
            ),
            Order(
                user_id=user.id,
                order_number="ORD-000003",
                status="completed",
                phone="+79990000001",
                shipping_address="Москва, Арбат 1",
                total_amount="200.00",
                created_at=datetime.now(timezone.utc),
            ),
            Order(
                user_id=other_user.id,
                order_number="ORD-000004",
                status="new",
                phone="+79990000002",
                shipping_address="Санкт-Петербург, Невский 1",
                total_amount="250.00",
                created_at=datetime.now(timezone.utc),
            ),
        ]
    )
    await db_session.commit()
    message = message_factory(telegram_id=user.telegram_id, text_value="Статус заказа")

    await show_active_order_statuses(message, db_session)

    message.answer.assert_awaited_once()
    response = message.answer.await_args.args[0]
    assert "Активные заказы:" in response
    assert "ORD-000001 - Принят" in response
    assert "ORD-000002 - Передан в доставку" in response
    assert "ORD-000003" not in response
    assert "ORD-000004" not in response


@pytest.mark.asyncio
async def test_show_active_order_statuses_shows_empty_state(db_session, message_factory) -> None:
    user = User(telegram_id=551003, username="buyer", first_name="Buyer", last_name="Two")
    db_session.add(user)
    await db_session.flush()
    db_session.add(
        Order(
            user_id=user.id,
            order_number="ORD-000005",
            status="cancelled",
            phone="+79990000003",
            shipping_address="Казань, Кремль 1",
            total_amount="300.00",
            created_at=datetime.now(timezone.utc),
        )
    )
    await db_session.commit()
    message = message_factory(telegram_id=user.telegram_id, text_value="Статус заказа")

    await show_active_order_statuses(message, db_session)

    message.answer.assert_awaited_once_with("У вас нет активных заказов.")


@pytest.mark.asyncio
async def test_show_active_order_statuses_handles_database_error(message_factory) -> None:
    message = message_factory(text_value="Статус заказа")
    db_session = AsyncMock()
    db_session.execute = AsyncMock(side_effect=SQLAlchemyError("boom"))

    await show_active_order_statuses(message, db_session)

    message.answer.assert_awaited_once_with(
        "Не удалось загрузить статусы заказов. Попробуйте позже."
    )
