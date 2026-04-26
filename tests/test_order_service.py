from decimal import Decimal

import pytest
from sqlalchemy import select

from app.models.category import Category
from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.product import Product
from app.models.user import User
from app.services.cart import add_product_to_cart, get_cart_by_telegram_id
from app.services.order import (
    CANONICAL_ORDER_STATUSES,
    EmptyCartError,
    InvalidAddressError,
    InvalidOrderStatusError,
    InvalidPhoneError,
    OrderStatusUpdateResult,
    create_order_from_cart,
    get_active_orders_by_telegram_id,
    get_active_orders_for_operator,
    get_order_by_id,
    normalize_address,
    normalize_phone,
    update_order_status,
    update_order_status_with_meta,
)


@pytest.mark.asyncio
async def test_create_order_from_cart_persists_order_and_clears_cart(db_session) -> None:
    user = User(telegram_id=331001, username="buyer", first_name="Buyer", last_name="One")
    category = Category(name="Одежда")
    db_session.add_all([user, category])
    await db_session.flush()
    first_product = Product(category_id=category.id, name="Футболка", price=Decimal("100.00"))
    second_product = Product(category_id=category.id, name="Худи", price=Decimal("250.00"))
    db_session.add_all([first_product, second_product])
    await db_session.commit()
    await add_product_to_cart(db_session, user.telegram_id, first_product.id)
    await add_product_to_cart(db_session, user.telegram_id, second_product.id)

    order = await create_order_from_cart(
        db_session,
        telegram_id=user.telegram_id,
        phone="8 (999) 123-45-67",
        shipping_address="Москва, Тверская 1",
    )

    assert order.order_number == "ORD-000001"
    assert order.total_amount == Decimal("350.00")

    order_result = await db_session.execute(select(Order).where(Order.id == order.id))
    saved_order = order_result.scalar_one()
    order_items_result = await db_session.execute(
        select(OrderItem).where(OrderItem.order_id == order.id)
    )
    saved_items = order_items_result.scalars().all()
    cart = await get_cart_by_telegram_id(db_session, user.telegram_id)

    assert saved_order.phone == "+79991234567"
    assert saved_order.shipping_address == "Москва, Тверская 1"
    assert len(saved_items) == 2
    assert {item.product_name for item in saved_items} == {"Футболка", "Худи"}
    assert cart is not None
    assert cart.items == []


@pytest.mark.asyncio
async def test_create_order_from_cart_raises_for_empty_cart(db_session) -> None:
    user = User(telegram_id=331002, username="empty", first_name="Empty", last_name="Cart")
    db_session.add(user)
    await db_session.commit()

    with pytest.raises(EmptyCartError):
        await create_order_from_cart(
            db_session,
            telegram_id=user.telegram_id,
            phone="+79991234567",
            shipping_address="Москва, Арбат 2",
        )


@pytest.mark.asyncio
async def test_get_active_orders_by_telegram_id_returns_only_active_orders_for_current_user(
    db_session,
) -> None:
    buyer = User(telegram_id=331003, username="buyer3", first_name="Buyer", last_name="Three")
    other_user = User(telegram_id=331004, username="other3", first_name="Other", last_name="Three")
    db_session.add_all([buyer, other_user])
    await db_session.flush()
    db_session.add_all(
        [
            Order(
                user_id=buyer.id,
                order_number="ORD-100001",
                status="new",
                phone="+79990000001",
                shipping_address="Москва, Тверская 10",
                total_amount=Decimal("100.00"),
            ),
            Order(
                user_id=buyer.id,
                order_number="ORD-100002",
                status="delivering",
                phone="+79990000001",
                shipping_address="Москва, Тверская 10",
                total_amount=Decimal("150.00"),
            ),
            Order(
                user_id=buyer.id,
                order_number="ORD-100003",
                status="completed",
                phone="+79990000001",
                shipping_address="Москва, Тверская 10",
                total_amount=Decimal("200.00"),
            ),
            Order(
                user_id=other_user.id,
                order_number="ORD-100004",
                status="new",
                phone="+79990000002",
                shipping_address="Казань, Баумана 5",
                total_amount=Decimal("250.00"),
            ),
        ]
    )
    await db_session.commit()

    orders = await get_active_orders_by_telegram_id(db_session, buyer.telegram_id)

    assert [order.order_number for order in orders] == ["ORD-100002", "ORD-100001"]


@pytest.mark.asyncio
async def test_get_active_orders_by_telegram_id_returns_empty_list_for_unknown_user(
    db_session,
) -> None:
    orders = await get_active_orders_by_telegram_id(db_session, telegram_id=999999)

    assert orders == []


@pytest.mark.asyncio
async def test_get_active_orders_for_operator_returns_only_non_terminal_orders(
    db_session,
) -> None:
    buyer = User(telegram_id=331005, username="buyer5", first_name="Buyer", last_name="Five")
    db_session.add(buyer)
    await db_session.flush()
    db_session.add_all(
        [
            Order(
                user_id=buyer.id,
                order_number="ORD-100010",
                status="new",
                phone="+79990000003",
                shipping_address="Москва, Ленина 1",
                total_amount=Decimal("100.00"),
            ),
            Order(
                user_id=buyer.id,
                order_number="ORD-100011",
                status="paid",
                phone="+79990000003",
                shipping_address="Москва, Ленина 1",
                total_amount=Decimal("100.00"),
            ),
            Order(
                user_id=buyer.id,
                order_number="ORD-100012",
                status="cancelled",
                phone="+79990000003",
                shipping_address="Москва, Ленина 1",
                total_amount=Decimal("100.00"),
            ),
        ]
    )
    await db_session.commit()

    orders = await get_active_orders_for_operator(db_session)

    assert [order.order_number for order in orders] == ["ORD-100011", "ORD-100010"]
    assert all(order.user is not None for order in orders)


@pytest.mark.asyncio
async def test_update_order_status_persists_new_status(db_session) -> None:
    buyer = User(telegram_id=331006, username="buyer6", first_name="Buyer", last_name="Six")
    db_session.add(buyer)
    await db_session.flush()
    order = Order(
        user_id=buyer.id,
        order_number="ORD-100020",
        status="new",
        phone="+79990000004",
        shipping_address="Казань, Кремль 1",
        total_amount=Decimal("250.00"),
    )
    db_session.add(order)
    await db_session.commit()

    updated_order = await update_order_status(db_session, order.id, "paid")
    persisted_order = await get_order_by_id(db_session, order.id)

    assert updated_order is not None
    assert updated_order.status == "paid"
    assert persisted_order is not None
    assert persisted_order.status == "paid"


@pytest.mark.asyncio
async def test_update_order_status_with_meta_marks_changed_transition(db_session) -> None:
    buyer = User(telegram_id=331016, username="buyer16", first_name="Buyer", last_name="Sixteen")
    db_session.add(buyer)
    await db_session.flush()
    order = Order(
        user_id=buyer.id,
        order_number="ORD-100021",
        status="new",
        phone="+79990000016",
        shipping_address="Тула, Советская 1",
        total_amount=Decimal("175.00"),
    )
    db_session.add(order)
    await db_session.commit()

    result = await update_order_status_with_meta(db_session, order.id, "paid")

    assert isinstance(result, OrderStatusUpdateResult)
    assert result.previous_status == "new"
    assert result.changed is True
    assert result.order.status == "paid"


@pytest.mark.asyncio
async def test_update_order_status_with_meta_skips_unchanged_status(db_session) -> None:
    buyer = User(telegram_id=331017, username="buyer17", first_name="Buyer", last_name="Seventeen")
    db_session.add(buyer)
    await db_session.flush()
    order = Order(
        user_id=buyer.id,
        order_number="ORD-100022",
        status="paid",
        phone="+79990000017",
        shipping_address="Омск, Мира 2",
        total_amount=Decimal("180.00"),
    )
    db_session.add(order)
    await db_session.commit()

    result = await update_order_status_with_meta(db_session, order.id, "paid")
    persisted_order = await get_order_by_id(db_session, order.id)

    assert isinstance(result, OrderStatusUpdateResult)
    assert result.previous_status == "paid"
    assert result.changed is False
    assert result.order.status == "paid"
    assert persisted_order is not None
    assert persisted_order.status == "paid"


@pytest.mark.asyncio
async def test_update_order_status_returns_none_for_missing_order(db_session) -> None:
    updated_order = await update_order_status(db_session, order_id=999999, status="paid")

    assert updated_order is None


def test_update_order_status_rejects_unknown_status() -> None:
    assert "paid" in CANONICAL_ORDER_STATUSES
    with pytest.raises(InvalidOrderStatusError):
        import asyncio
        from unittest.mock import AsyncMock

        asyncio.run(update_order_status(AsyncMock(), order_id=1, status="mystery"))


def test_normalize_phone_rejects_short_number() -> None:
    with pytest.raises(InvalidPhoneError):
        normalize_phone("12345")


def test_normalize_address_rejects_too_short_value() -> None:
    with pytest.raises(InvalidAddressError):
        normalize_address("дом")
