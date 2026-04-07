from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from sqlalchemy.exc import SQLAlchemyError

from app.callbacks.cart import CartCallback, DECREASE_ACTION, INCREASE_ACTION, REMOVE_ACTION
from app.handlers import cart as cart_module
from app.handlers.cart import decrease_item, increase_item, open_cart, remove_item
from app.models.cart import Cart
from app.models.cart_item import CartItem
from app.models.category import Category
from app.models.product import Product
from app.models.user import User


async def _seed_cart(db_session) -> tuple[User, CartItem]:
    user = User(
        telegram_id=222001,
        username="cart_user",
        first_name="Cart",
        last_name="User",
    )
    category = Category(name="Футболки")
    db_session.add_all([user, category])
    await db_session.flush()
    product = Product(category_id=category.id, name="Белая футболка", price=Decimal("1999.00"))
    db_session.add(product)
    await db_session.flush()
    cart = Cart(user_id=user.id)
    db_session.add(cart)
    await db_session.flush()
    cart_item = CartItem(cart_id=cart.id, product_id=product.id, quantity=1)
    db_session.add(cart_item)
    await db_session.commit()
    return user, cart_item


@pytest.mark.asyncio
async def test_open_cart_shows_empty_cart(db_session, message_factory) -> None:
    message = message_factory(text_value="Корзина")

    await open_cart(message, db_session)

    message.answer.assert_awaited_once_with("Корзина пуста.")


@pytest.mark.asyncio
async def test_open_cart_shows_items(db_session, message_factory) -> None:
    user, _cart_item = await _seed_cart(db_session)
    message = message_factory(
        telegram_id=user.telegram_id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name,
        text_value="Корзина",
    )

    await open_cart(message, db_session)

    message.answer.assert_awaited_once()
    assert "Белая футболка" in message.answer.await_args.args[0]
    assert "Итого: 1999.00 ₽" in message.answer.await_args.args[0]


@pytest.mark.asyncio
async def test_increase_item_updates_cart(db_session, callback_factory) -> None:
    user, cart_item = await _seed_cart(db_session)
    callback = callback_factory()
    callback.from_user = SimpleNamespace(id=user.telegram_id)
    callback_data = CartCallback(action=INCREASE_ACTION, cart_item_id=cart_item.id)

    await increase_item(callback, callback_data, db_session)

    callback.message.edit_text.assert_awaited_once()
    assert "Количество: 2" in callback.message.edit_text.await_args.args[0]


@pytest.mark.asyncio
async def test_decrease_item_removes_last_position_and_shows_empty(db_session, callback_factory) -> None:
    user, cart_item = await _seed_cart(db_session)
    callback = callback_factory()
    callback.from_user = SimpleNamespace(id=user.telegram_id)
    callback_data = CartCallback(action=DECREASE_ACTION, cart_item_id=cart_item.id)

    await decrease_item(callback, callback_data, db_session)

    callback.message.edit_text.assert_awaited_once_with("Корзина пуста.")


@pytest.mark.asyncio
async def test_remove_item_updates_cart(db_session, callback_factory) -> None:
    user, cart_item = await _seed_cart(db_session)
    callback = callback_factory()
    callback.from_user = SimpleNamespace(id=user.telegram_id)
    callback_data = CartCallback(action=REMOVE_ACTION, cart_item_id=cart_item.id)

    await remove_item(callback, callback_data, db_session)

    callback.message.edit_text.assert_awaited_once_with("Корзина пуста.")


@pytest.mark.asyncio
async def test_cart_action_handles_missing_item(db_session, callback_factory) -> None:
    callback = callback_factory()
    callback.from_user = SimpleNamespace(id=222001)
    callback_data = CartCallback(action=INCREASE_ACTION, cart_item_id=999)

    await increase_item(callback, callback_data, db_session)

    callback.message.edit_text.assert_awaited_once_with("Позиция корзины не найдена.")


@pytest.mark.asyncio
async def test_open_cart_handles_database_error(message_factory, monkeypatch) -> None:
    message = message_factory(text_value="Корзина")

    async def broken_get_cart(_session, _telegram_id):
        raise SQLAlchemyError("boom")

    monkeypatch.setattr(cart_module, "get_cart_by_telegram_id", broken_get_cart)

    await open_cart(message, AsyncMock())

    message.answer.assert_awaited_once_with("Не удалось обновить корзину. Попробуйте позже.")
