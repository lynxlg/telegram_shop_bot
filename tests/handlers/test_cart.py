from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from sqlalchemy.exc import SQLAlchemyError

from app.callbacks.cart import (
    DECREASE_ACTION,
    INCREASE_ACTION,
    REMOVE_ACTION,
    CartCallback,
)
from app.handlers import cart as cart_module
from app.handlers.cart import (
    cancel_checkout_by_callback,
    clear_items,
    confirm_checkout,
    decrease_item,
    increase_item,
    open_cart,
    receive_checkout_address,
    receive_checkout_phone,
    remove_item,
    start_checkout,
)
from app.keyboards.main_menu import get_main_menu_keyboard
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
async def test_decrease_item_removes_last_position_and_shows_empty(
    db_session, callback_factory
) -> None:
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
async def test_clear_items_updates_cart(db_session, callback_factory) -> None:
    user, _cart_item = await _seed_cart(db_session)
    callback = callback_factory()
    callback.from_user = SimpleNamespace(id=user.telegram_id)

    await clear_items(callback, db_session)

    callback.message.edit_text.assert_awaited_once_with("Корзина пуста.")


@pytest.mark.asyncio
async def test_clear_items_shows_empty_cart_when_already_empty(
    db_session, callback_factory
) -> None:
    callback = callback_factory()
    callback.from_user = SimpleNamespace(id=222001)

    await clear_items(callback, db_session)

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


@pytest.mark.asyncio
async def test_start_checkout_requests_phone_unit(callback_factory, monkeypatch) -> None:
    callback = callback_factory()
    callback.from_user = SimpleNamespace(id=222001)
    state = AsyncMock()
    fake_cart = SimpleNamespace(items=[SimpleNamespace(id=1)])

    async def fake_get_cart(_db, _telegram_id):
        return fake_cart

    async def fake_get_user_phone(_db, _telegram_id):
        return "+79991234567"

    monkeypatch.setattr(cart_module, "get_cart_by_telegram_id", fake_get_cart)
    monkeypatch.setattr(cart_module, "_get_user_phone", fake_get_user_phone)

    await start_checkout(callback, state, AsyncMock())

    state.set_state.assert_awaited_once()
    state.update_data.assert_awaited_once_with(saved_phone="+79991234567")
    callback.message.answer.assert_awaited_once()
    assert "Введите номер телефона" in callback.message.answer.await_args.args[0]


@pytest.mark.asyncio
async def test_start_checkout_requests_phone(db_session, callback_factory) -> None:
    user, _cart_item = await _seed_cart(db_session)
    callback = callback_factory()
    callback.from_user = SimpleNamespace(id=user.telegram_id)
    state = AsyncMock()

    await start_checkout(callback, state, db_session)

    state.set_state.assert_awaited_once()
    callback.message.answer.assert_awaited_once()
    assert "Введите номер телефона" in callback.message.answer.await_args.args[0]


@pytest.mark.asyncio
async def test_receive_checkout_phone_moves_to_address_step(db_session, message_factory) -> None:
    user, _cart_item = await _seed_cart(db_session)
    message = message_factory(
        telegram_id=user.telegram_id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name,
        text_value="+7 999 123 45 67",
    )
    state = AsyncMock()

    await receive_checkout_phone(message, state, db_session)

    state.update_data.assert_awaited_once_with(phone="+79991234567")
    state.set_state.assert_awaited_once()
    assert "Введите адрес доставки." in message.answer.await_args.args[0]


@pytest.mark.asyncio
async def test_receive_checkout_address_shows_confirmation(db_session, message_factory) -> None:
    user, _cart_item = await _seed_cart(db_session)
    message = message_factory(
        telegram_id=user.telegram_id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name,
        text_value="Москва, Тверская 1",
    )
    state = AsyncMock()
    state.get_data.return_value = {"phone": "+79991234567"}

    await receive_checkout_address(message, state, db_session)

    state.set_state.assert_awaited_once()
    message.answer.assert_awaited_once()
    assert "Подтвердите заказ:" in message.answer.await_args.args[0]


@pytest.mark.asyncio
async def test_confirm_checkout_creates_order(db_session, callback_factory) -> None:
    user, _cart_item = await _seed_cart(db_session)
    callback = callback_factory()
    callback.from_user = SimpleNamespace(id=user.telegram_id)
    state = AsyncMock()
    state.get_data.return_value = {
        "phone": "+79991234567",
        "shipping_address": "Москва, Тверская 1",
    }

    await confirm_checkout(callback, state, db_session)

    state.clear.assert_awaited_once()
    callback.message.edit_text.assert_awaited_once_with(
        "Заказ оформлен.\nНомер заказа: ORD-000001",
        reply_markup=None,
    )
    callback.message.answer.assert_awaited_once_with(
        "Выберите действие в главном меню.",
        reply_markup=get_main_menu_keyboard(),
    )


@pytest.mark.asyncio
async def test_confirm_checkout_success_unit(callback_factory, monkeypatch) -> None:
    callback = callback_factory()
    callback.from_user = SimpleNamespace(id=222001)
    state = AsyncMock()
    state.get_data.return_value = {
        "phone": "+79991234567",
        "shipping_address": "Москва, Тверская 1",
    }

    async def fake_create_order(_db, _telegram_id, phone, shipping_address):
        assert phone == "+79991234567"
        assert shipping_address == "Москва, Тверская 1"
        return SimpleNamespace(order_number="ORD-000321")

    monkeypatch.setattr(cart_module, "create_order_from_cart", fake_create_order)
    monkeypatch.setattr(cart_module, "_get_user_role", AsyncMock(return_value="user"))

    await confirm_checkout(callback, state, AsyncMock())

    state.clear.assert_awaited_once()
    callback.message.edit_text.assert_awaited_once_with(
        "Заказ оформлен.\nНомер заказа: ORD-000321",
        reply_markup=None,
    )
    callback.message.answer.assert_awaited_once_with(
        "Выберите действие в главном меню.",
        reply_markup=get_main_menu_keyboard(),
    )


@pytest.mark.asyncio
async def test_cancel_checkout_by_callback_restores_cart(db_session, callback_factory) -> None:
    user, _cart_item = await _seed_cart(db_session)
    callback = callback_factory()
    callback.from_user = SimpleNamespace(id=user.telegram_id)
    state = AsyncMock()

    await cancel_checkout_by_callback(callback, state, db_session)

    state.clear.assert_awaited_once()
    callback.message.edit_text.assert_awaited_once()
    assert "Белая футболка" in callback.message.edit_text.await_args.args[0]
