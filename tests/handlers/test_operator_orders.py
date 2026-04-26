from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from sqlalchemy.exc import SQLAlchemyError

from app.callbacks.operator_orders import (
    OPEN_ORDER_ACTION,
    UPDATE_STATUS_ACTION,
    OperatorOrdersCallback,
)
from app.handlers import operator_orders as operator_orders_module
from app.handlers.operator_orders import (
    back_to_operator_orders,
    change_operator_order_status,
    open_operator_order,
    show_operator_orders,
)
from app.models.order import Order
from app.models.user import User


@pytest.mark.asyncio
async def test_show_operator_orders_unit_access_denied(message_factory, monkeypatch) -> None:
    message = message_factory(text_value="Заказы")

    async def fake_is_operator(_db, _telegram_id):
        return False

    monkeypatch.setattr(operator_orders_module, "_is_operator", fake_is_operator)

    await show_operator_orders(message, AsyncMock())

    message.answer.assert_awaited_once_with("У вас нет доступа к управлению заказами.")


@pytest.mark.asyncio
async def test_show_operator_orders_unit_happy_path(message_factory, monkeypatch) -> None:
    message = message_factory(text_value="Заказы")

    async def fake_is_operator(_db, _telegram_id):
        return True

    async def fake_get_active_orders(_db):
        return [
            SimpleNamespace(
                id=1,
                order_number="ORD-800001",
                status="new",
                user=SimpleNamespace(first_name="Анна"),
            ),
            SimpleNamespace(
                id=2,
                order_number="ORD-800002",
                status="paid",
                user=SimpleNamespace(first_name="Борис"),
            ),
        ]

    monkeypatch.setattr(operator_orders_module, "_is_operator", fake_is_operator)
    monkeypatch.setattr(
        operator_orders_module,
        "get_active_orders_for_operator",
        fake_get_active_orders,
    )

    await show_operator_orders(message, AsyncMock())

    message.answer.assert_awaited_once()
    response = message.answer.await_args.args[0]
    assert "ORD-800001 - Анна - Создан" in response
    assert "ORD-800002 - Борис - Оплачен" in response


@pytest.mark.asyncio
async def test_change_operator_order_status_unit_happy_path(callback_factory, monkeypatch) -> None:
    callback = callback_factory()
    callback.from_user = type("UserObj", (), {"id": 990001})()
    bot = AsyncMock()

    async def fake_is_operator(_db, _telegram_id):
        return True

    async def fake_update_order_status(_db, _order_id, _status):
        return SimpleNamespace(
            order=SimpleNamespace(
                id=1,
                order_number="ORD-800010",
                status="paid",
                phone="+79990000001",
                shipping_address="Москва, Тверская 1",
                total_amount=1500,
                user=SimpleNamespace(first_name="Анна", telegram_id=990010),
            ),
            previous_status="new",
            changed=True,
        )

    monkeypatch.setattr(operator_orders_module, "_is_operator", fake_is_operator)
    monkeypatch.setattr(
        operator_orders_module,
        "update_order_status_with_meta",
        fake_update_order_status,
    )

    await change_operator_order_status(
        callback,
        OperatorOrdersCallback(action=UPDATE_STATUS_ACTION, order_id=1, status="paid"),
        AsyncMock(),
        bot,
    )

    callback.message.edit_text.assert_awaited_once()
    assert "Статус: Оплачен" in callback.message.edit_text.await_args.args[0]
    bot.send_message.assert_awaited_once_with(
        990010,
        "Статус заказа ORD-800010 обновлен: Оплачен.",
    )


@pytest.mark.asyncio
async def test_change_operator_order_status_unit_does_not_notify_when_status_unchanged(
    callback_factory,
    monkeypatch,
) -> None:
    callback = callback_factory()
    callback.from_user = type("UserObj", (), {"id": 990002})()
    bot = AsyncMock()

    async def fake_is_operator(_db, _telegram_id):
        return True

    async def fake_update_order_status(_db, _order_id, _status):
        return SimpleNamespace(
            order=SimpleNamespace(
                id=2,
                order_number="ORD-800011",
                status="paid",
                phone="+79990000002",
                shipping_address="Москва, Тверская 2",
                total_amount=1800,
                user=SimpleNamespace(first_name="Борис", telegram_id=990011),
            ),
            previous_status="paid",
            changed=False,
        )

    monkeypatch.setattr(operator_orders_module, "_is_operator", fake_is_operator)
    monkeypatch.setattr(
        operator_orders_module,
        "update_order_status_with_meta",
        fake_update_order_status,
    )

    await change_operator_order_status(
        callback,
        OperatorOrdersCallback(action=UPDATE_STATUS_ACTION, order_id=2, status="paid"),
        AsyncMock(),
        bot,
    )

    callback.message.edit_text.assert_awaited_once()
    bot.send_message.assert_not_awaited()


@pytest.mark.asyncio
async def test_change_operator_order_status_unit_ignores_notification_failure(
    callback_factory,
    monkeypatch,
) -> None:
    callback = callback_factory()
    callback.from_user = type("UserObj", (), {"id": 990003})()
    bot = AsyncMock()

    async def fake_is_operator(_db, _telegram_id):
        return True

    async def fake_update_order_status(_db, _order_id, _status):
        return SimpleNamespace(
            order=SimpleNamespace(
                id=3,
                order_number="ORD-800012",
                status="assembling",
                phone="+79990000003",
                shipping_address="Москва, Тверская 3",
                total_amount=2100,
                user=SimpleNamespace(first_name="Вера", telegram_id=990012),
            ),
            previous_status="paid",
            changed=True,
        )

    bot.send_message.side_effect = RuntimeError("telegram down")

    monkeypatch.setattr(operator_orders_module, "_is_operator", fake_is_operator)
    monkeypatch.setattr(
        operator_orders_module,
        "update_order_status_with_meta",
        fake_update_order_status,
    )

    await change_operator_order_status(
        callback,
        OperatorOrdersCallback(action=UPDATE_STATUS_ACTION, order_id=3, status="assembling"),
        AsyncMock(),
        bot,
    )

    callback.message.edit_text.assert_awaited_once()
    callback.answer.assert_awaited_once()
    bot.send_message.assert_awaited_once()


@pytest.mark.asyncio
async def test_show_operator_orders_denies_regular_user(db_session, message_factory) -> None:
    user = User(
        telegram_id=771001, username="buyer", first_name="Buyer", last_name="One", role="user"
    )
    db_session.add(user)
    await db_session.commit()
    message = message_factory(telegram_id=user.telegram_id, text_value="Заказы")

    await show_operator_orders(message, db_session)

    message.answer.assert_awaited_once_with("У вас нет доступа к управлению заказами.")


@pytest.mark.asyncio
async def test_show_operator_orders_lists_active_orders_for_operator(
    db_session,
    message_factory,
) -> None:
    operator = User(
        telegram_id=771002, username="operator", first_name="Оля", last_name="Оп", role="operator"
    )
    buyer = User(telegram_id=771003, username="buyer2", first_name="Иван", last_name="Покупатель")
    db_session.add_all([operator, buyer])
    await db_session.flush()
    db_session.add_all(
        [
            Order(
                user_id=buyer.id,
                order_number="ORD-700001",
                status="new",
                phone="+79990000001",
                shipping_address="Москва, Арбат 1",
                total_amount="100.00",
                created_at=datetime.now(timezone.utc),
            ),
            Order(
                user_id=buyer.id,
                order_number="ORD-700002",
                status="paid",
                phone="+79990000001",
                shipping_address="Москва, Арбат 1",
                total_amount="150.00",
                created_at=datetime.now(timezone.utc),
            ),
            Order(
                user_id=buyer.id,
                order_number="ORD-700003",
                status="completed",
                phone="+79990000001",
                shipping_address="Москва, Арбат 1",
                total_amount="150.00",
                created_at=datetime.now(timezone.utc),
            ),
        ]
    )
    await db_session.commit()
    message = message_factory(telegram_id=operator.telegram_id, text_value="Заказы")

    await show_operator_orders(message, db_session)

    message.answer.assert_awaited_once()
    response = message.answer.await_args.args[0]
    reply_markup = message.answer.await_args.kwargs["reply_markup"]
    assert "Активные заказы для обработки:" in response
    assert "ORD-700001 - Иван - Создан" in response
    assert "ORD-700002 - Иван - Оплачен" in response
    assert "ORD-700003" not in response
    assert reply_markup.inline_keyboard[0][0].text == "ORD-700002"


@pytest.mark.asyncio
async def test_open_operator_order_shows_details_and_status_buttons(
    db_session,
    callback_factory,
) -> None:
    operator = User(
        telegram_id=771004, username="operator4", first_name="Оля", last_name="Оп", role="operator"
    )
    buyer = User(telegram_id=771005, username="buyer5", first_name="Мария", last_name="Покупатель")
    db_session.add_all([operator, buyer])
    await db_session.flush()
    order = Order(
        user_id=buyer.id,
        order_number="ORD-700010",
        status="new",
        phone="+79990000009",
        shipping_address="Казань, Баумана 5",
        total_amount="900.00",
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(order)
    await db_session.commit()
    callback = callback_factory()
    callback.from_user = type("UserObj", (), {"id": operator.telegram_id})()

    await open_operator_order(
        callback,
        OperatorOrdersCallback(action=OPEN_ORDER_ACTION, order_id=order.id),
        db_session,
    )

    callback.message.edit_text.assert_awaited_once()
    text = callback.message.edit_text.await_args.args[0]
    markup = callback.message.edit_text.await_args.kwargs["reply_markup"]
    assert "Заказ: ORD-700010" in text
    assert "Покупатель: Мария" in text
    assert "Статус: Создан" in text
    assert any(button.text == "• Создан" for row in markup.inline_keyboard for button in row)
    assert any(button.text == "Оплачен" for row in markup.inline_keyboard for button in row)


@pytest.mark.asyncio
async def test_change_operator_order_status_updates_order(
    db_session,
    callback_factory,
) -> None:
    operator = User(
        telegram_id=771006, username="operator6", first_name="Павел", last_name="Оп", role="admin"
    )
    buyer = User(telegram_id=771007, username="buyer7", first_name="Ирина", last_name="Покупатель")
    db_session.add_all([operator, buyer])
    await db_session.flush()
    order = Order(
        user_id=buyer.id,
        order_number="ORD-700020",
        status="new",
        phone="+79990000010",
        shipping_address="Самара, Ленина 1",
        total_amount="1200.00",
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(order)
    await db_session.commit()
    callback = callback_factory()
    callback.from_user = type("UserObj", (), {"id": operator.telegram_id})()
    bot = AsyncMock()

    await change_operator_order_status(
        callback,
        OperatorOrdersCallback(
            action=UPDATE_STATUS_ACTION,
            order_id=order.id,
            status="paid",
        ),
        db_session,
        bot,
    )

    callback.message.edit_text.assert_awaited_once()
    response = callback.message.edit_text.await_args.args[0]
    assert "Статус: Оплачен" in response
    bot.send_message.assert_awaited_once_with(
        buyer.telegram_id,
        "Статус заказа ORD-700020 обновлен: Оплачен.",
    )


@pytest.mark.asyncio
async def test_back_to_operator_orders_hides_terminal_order_after_update(
    db_session,
    callback_factory,
) -> None:
    operator = User(
        telegram_id=771008, username="operator8", first_name="Анна", last_name="Оп", role="operator"
    )
    buyer = User(telegram_id=771009, username="buyer9", first_name="Петр", last_name="Покупатель")
    db_session.add_all([operator, buyer])
    await db_session.flush()
    first_order = Order(
        user_id=buyer.id,
        order_number="ORD-700030",
        status="completed",
        phone="+79990000011",
        shipping_address="Омск, Мира 2",
        total_amount="800.00",
        created_at=datetime.now(timezone.utc),
    )
    second_order = Order(
        user_id=buyer.id,
        order_number="ORD-700031",
        status="delivering",
        phone="+79990000011",
        shipping_address="Омск, Мира 2",
        total_amount="900.00",
        created_at=datetime.now(timezone.utc),
    )
    db_session.add_all([first_order, second_order])
    await db_session.commit()
    callback = callback_factory()
    callback.from_user = type("UserObj", (), {"id": operator.telegram_id})()

    await back_to_operator_orders(
        callback,
        db_session,
    )

    callback.message.edit_text.assert_awaited_once()
    response = callback.message.edit_text.await_args.args[0]
    assert "ORD-700030" not in response
    assert "ORD-700031" in response


@pytest.mark.asyncio
async def test_operator_callbacks_denied_for_regular_user(
    db_session,
    callback_factory,
) -> None:
    user = User(
        telegram_id=771010, username="buyer10", first_name="Buyer", last_name="Ten", role="user"
    )
    db_session.add(user)
    await db_session.commit()
    callback = callback_factory()
    callback.from_user = type("UserObj", (), {"id": user.telegram_id})()
    bot = AsyncMock()

    await open_operator_order(
        callback,
        OperatorOrdersCallback(action=OPEN_ORDER_ACTION, order_id=1),
        db_session,
    )

    callback.answer.assert_awaited_once_with(
        "У вас нет доступа к управлению заказами.",
        show_alert=True,
    )

    callback.answer.reset_mock()
    await change_operator_order_status(
        callback,
        OperatorOrdersCallback(action=UPDATE_STATUS_ACTION, order_id=1, status="paid"),
        db_session,
        bot,
    )
    callback.answer.assert_awaited_once_with(
        "У вас нет доступа к управлению заказами.",
        show_alert=True,
    )
    bot.send_message.assert_not_awaited()


@pytest.mark.asyncio
async def test_show_operator_orders_handles_database_error(message_factory) -> None:
    message = message_factory(text_value="Заказы")
    db_session = AsyncMock()
    db_session.execute = AsyncMock(side_effect=SQLAlchemyError("boom"))

    await show_operator_orders(message, db_session)

    message.answer.assert_awaited_once_with("Не удалось загрузить заказы. Попробуйте позже.")
