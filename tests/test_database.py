from decimal import Decimal

import pytest
from sqlalchemy import inspect, select, text
from sqlalchemy.exc import IntegrityError

from app.models.cart import Cart
from app.models.cart_item import CartItem
from app.models.category import Category
from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.payment_attempt import PaymentAttempt
from app.models.product import Product
from app.models.user import User


@pytest.mark.asyncio
async def test_database_connection_successful(test_engine) -> None:
    async with test_engine.connect() as connection:
        result = await connection.execute(text("SELECT 1"))

    assert result.scalar_one() == 1


@pytest.mark.asyncio
async def test_tables_created(test_engine) -> None:
    async with test_engine.begin() as connection:
        tables = await connection.run_sync(
            lambda sync_connection: inspect(sync_connection).get_table_names()
        )

    assert "users" in tables
    assert "products" in tables
    assert "categories" in tables
    assert "product_attributes" in tables
    assert "carts" in tables
    assert "cart_items" in tables
    assert "orders" in tables
    assert "order_items" in tables
    assert "payment_attempts" in tables


@pytest.mark.asyncio
async def test_products_table_contains_image_url_column(test_engine) -> None:
    async with test_engine.begin() as connection:
        columns = await connection.run_sync(
            lambda sync_connection: inspect(sync_connection).get_columns("products")
        )

    column_names = [column["name"] for column in columns]

    assert "image_url" in column_names


@pytest.mark.asyncio
async def test_user_persist_and_load(db_session) -> None:
    user = User(
        telegram_id=777000,
        username="persisted_user",
        first_name="Persisted",
        last_name="User",
    )

    db_session.add(user)
    await db_session.commit()

    result = await db_session.execute(select(User).where(User.telegram_id == 777000))
    saved_user = result.scalar_one()

    assert saved_user.username == "persisted_user"
    assert saved_user.first_name == "Persisted"
    assert saved_user.last_name == "User"


@pytest.mark.asyncio
async def test_telegram_id_unique_constraint(db_session) -> None:
    first_user = User(
        telegram_id=100500,
        username="first_user",
        first_name="First",
        last_name="User",
    )
    second_user = User(
        telegram_id=100500,
        username="second_user",
        first_name="Second",
        last_name="User",
    )

    db_session.add(first_user)
    await db_session.commit()

    db_session.add(second_user)

    with pytest.raises(IntegrityError):
        await db_session.commit()

    await db_session.rollback()


@pytest.mark.asyncio
async def test_product_persist_and_load_with_image_url(db_session) -> None:
    category = Category(name="Футболки")
    db_session.add(category)
    await db_session.flush()
    product = Product(
        category_id=category.id,
        name="Белая футболка",
        price="1999.00",
        image_url="https://example.com/products/white-tshirt.jpg",
    )

    db_session.add(product)
    await db_session.commit()

    result = await db_session.execute(select(Product).where(Product.id == product.id))
    saved_product = result.scalar_one()

    assert saved_product.image_url == "https://example.com/products/white-tshirt.jpg"


@pytest.mark.asyncio
async def test_cart_item_persist_and_load(db_session) -> None:
    user = User(
        telegram_id=555001,
        username="cart_user",
        first_name="Cart",
        last_name="User",
    )
    category = Category(name="Футболки")
    db_session.add_all([user, category])
    await db_session.flush()
    product = Product(
        category_id=category.id,
        name="Белая футболка",
        price="1999.00",
    )
    db_session.add(product)
    await db_session.flush()
    cart = Cart(user_id=user.id)
    db_session.add(cart)
    await db_session.flush()
    cart_item = CartItem(cart_id=cart.id, product_id=product.id, quantity=2)
    db_session.add(cart_item)
    await db_session.commit()

    result = await db_session.execute(select(CartItem).where(CartItem.id == cart_item.id))
    saved_cart_item = result.scalar_one()

    assert saved_cart_item.quantity == 2


@pytest.mark.asyncio
async def test_carts_user_id_unique_constraint(db_session) -> None:
    user = User(
        telegram_id=555002,
        username="one_cart_user",
        first_name="One",
        last_name="Cart",
    )
    db_session.add(user)
    await db_session.flush()
    db_session.add_all([Cart(user_id=user.id), Cart(user_id=user.id)])

    with pytest.raises(IntegrityError):
        await db_session.commit()

    await db_session.rollback()


@pytest.mark.asyncio
async def test_order_persist_and_load_with_items(db_session) -> None:
    user = User(
        telegram_id=555003,
        username="order_user",
        first_name="Order",
        last_name="User",
    )
    category = Category(name="Толстовки")
    db_session.add_all([user, category])
    await db_session.flush()
    product = Product(
        category_id=category.id,
        name="Черное худи",
        price="2999.00",
    )
    db_session.add(product)
    await db_session.flush()
    order = Order(
        user_id=user.id,
        order_number="ORD-000777",
        status="new",
        phone="+79991234567",
        shipping_address="Москва, Пушкина 10",
        total_amount=Decimal("2999.00"),
    )
    db_session.add(order)
    await db_session.flush()
    order_item = OrderItem(
        order_id=order.id,
        product_id=product.id,
        product_name=product.name,
        unit_price=product.price,
        quantity=1,
        line_total=product.price,
    )
    db_session.add(order_item)
    await db_session.commit()

    order_result = await db_session.execute(select(Order).where(Order.id == order.id))
    saved_order = order_result.scalar_one()
    items_result = await db_session.execute(select(OrderItem).where(OrderItem.order_id == order.id))
    saved_item = items_result.scalar_one()

    assert saved_order.order_number == "ORD-000777"
    assert saved_order.total_amount == Decimal("2999.00")
    assert saved_item.product_name == "Черное худи"


@pytest.mark.asyncio
async def test_payment_attempt_persist_and_load(db_session) -> None:
    user = User(
        telegram_id=555004,
        username="payment_user",
        first_name="Payment",
        last_name="User",
    )
    db_session.add(user)
    await db_session.flush()
    order = Order(
        user_id=user.id,
        order_number="ORD-000778",
        status="new",
        phone="+79991234568",
        shipping_address="Москва, Пушкина 11",
        total_amount=Decimal("1999.00"),
    )
    db_session.add(order)
    await db_session.flush()
    attempt = PaymentAttempt(
        order_id=order.id,
        provider="yookassa",
        provider_payment_id="pay_0001",
        idempotence_key="idem_0001",
        status="pending",
        amount=Decimal("1999.00"),
        currency="RUB",
        confirmation_url="https://pay.example/1",
    )
    db_session.add(attempt)
    await db_session.commit()

    result = await db_session.execute(
        select(PaymentAttempt).where(PaymentAttempt.provider_payment_id == "pay_0001")
    )
    saved_attempt = result.scalar_one()

    assert saved_attempt.order_id == order.id
    assert saved_attempt.status == "pending"
