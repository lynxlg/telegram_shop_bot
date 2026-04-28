from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.models.cart_item import CartItem
from app.models.category import Category
from app.models.product import Product
from app.models.user import User
from app.services.cart import (
    add_product_to_cart,
    clear_cart,
    decrease_cart_item_quantity,
    get_cart_by_telegram_id,
    increase_cart_item_quantity,
    remove_cart_item,
)


@pytest.mark.asyncio
async def test_add_product_to_cart_creates_cart_and_item(db_session) -> None:
    user = User(telegram_id=111001, username="user", first_name="User", last_name="One")
    category = Category(name="Одежда")
    db_session.add_all([user, category])
    await db_session.flush()
    product = Product(category_id=category.id, name="Футболка", price=Decimal("100.00"))
    db_session.add(product)
    await db_session.commit()

    cart_item = await add_product_to_cart(db_session, user.telegram_id, product.id)

    assert cart_item is not None
    assert cart_item.quantity == 1


@pytest.mark.asyncio
async def test_add_product_to_cart_increases_existing_quantity(db_session) -> None:
    user = User(telegram_id=111002, username="user", first_name="User", last_name="Two")
    category = Category(name="Одежда")
    db_session.add_all([user, category])
    await db_session.flush()
    product = Product(category_id=category.id, name="Футболка", price=Decimal("100.00"))
    db_session.add(product)
    await db_session.commit()

    await add_product_to_cart(db_session, user.telegram_id, product.id)
    cart_item = await add_product_to_cart(db_session, user.telegram_id, product.id)

    assert cart_item is not None
    assert cart_item.quantity == 2


@pytest.mark.asyncio
async def test_get_cart_by_telegram_id_returns_saved_items(db_session) -> None:
    user = User(telegram_id=111003, username="user", first_name="User", last_name="Three")
    category = Category(name="Одежда")
    db_session.add_all([user, category])
    await db_session.flush()
    product = Product(category_id=category.id, name="Футболка", price=Decimal("100.00"))
    db_session.add(product)
    await db_session.commit()
    await add_product_to_cart(db_session, user.telegram_id, product.id)

    cart = await get_cart_by_telegram_id(db_session, user.telegram_id)

    assert cart is not None
    assert len(cart.items) == 1
    assert cart.items[0].product.name == "Футболка"


@pytest.mark.asyncio
async def test_increase_cart_item_quantity(db_session) -> None:
    user = User(telegram_id=111004, username="user", first_name="User", last_name="Four")
    category = Category(name="Одежда")
    db_session.add_all([user, category])
    await db_session.flush()
    product = Product(category_id=category.id, name="Футболка", price=Decimal("100.00"))
    db_session.add(product)
    await db_session.commit()
    cart_item = await add_product_to_cart(db_session, user.telegram_id, product.id)

    updated_item = await increase_cart_item_quantity(db_session, cart_item.id)

    assert updated_item is not None
    assert updated_item.quantity == 2


@pytest.mark.asyncio
async def test_decrease_cart_item_quantity(db_session) -> None:
    user = User(telegram_id=111005, username="user", first_name="User", last_name="Five")
    category = Category(name="Одежда")
    db_session.add_all([user, category])
    await db_session.flush()
    product = Product(category_id=category.id, name="Футболка", price=Decimal("100.00"))
    db_session.add(product)
    await db_session.commit()
    cart_item = await add_product_to_cart(db_session, user.telegram_id, product.id)
    await increase_cart_item_quantity(db_session, cart_item.id)

    updated_item = await decrease_cart_item_quantity(db_session, cart_item.id)

    assert updated_item is not None
    assert updated_item.quantity == 1


@pytest.mark.asyncio
async def test_decrease_cart_item_quantity_removes_item_on_one(db_session) -> None:
    user = User(telegram_id=111006, username="user", first_name="User", last_name="Six")
    category = Category(name="Одежда")
    db_session.add_all([user, category])
    await db_session.flush()
    product = Product(category_id=category.id, name="Футболка", price=Decimal("100.00"))
    db_session.add(product)
    await db_session.commit()
    cart_item = await add_product_to_cart(db_session, user.telegram_id, product.id)

    updated_item = await decrease_cart_item_quantity(db_session, cart_item.id)
    result = await db_session.execute(select(CartItem).where(CartItem.id == cart_item.id))

    assert updated_item is None
    assert result.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_remove_cart_item(db_session) -> None:
    user = User(telegram_id=111007, username="user", first_name="User", last_name="Seven")
    category = Category(name="Одежда")
    db_session.add_all([user, category])
    await db_session.flush()
    product = Product(category_id=category.id, name="Футболка", price=Decimal("100.00"))
    db_session.add(product)
    await db_session.commit()
    cart_item = await add_product_to_cart(db_session, user.telegram_id, product.id)

    removed = await remove_cart_item(db_session, cart_item.id)

    assert removed is True


@pytest.mark.asyncio
async def test_clear_cart_removes_all_items(db_session) -> None:
    user = User(telegram_id=111010, username="user", first_name="User", last_name="Ten")
    category = Category(name="Одежда")
    db_session.add_all([user, category])
    await db_session.flush()
    first_product = Product(category_id=category.id, name="Футболка", price=Decimal("100.00"))
    second_product = Product(category_id=category.id, name="Худи", price=Decimal("200.00"))
    db_session.add_all([first_product, second_product])
    await db_session.commit()
    await add_product_to_cart(db_session, user.telegram_id, first_product.id)
    await add_product_to_cart(db_session, user.telegram_id, second_product.id)

    cleared = await clear_cart(db_session, user.telegram_id)
    cart = await get_cart_by_telegram_id(db_session, user.telegram_id)

    assert cleared is True
    assert cart is not None
    assert cart.items == []


@pytest.mark.asyncio
async def test_add_product_to_cart_returns_none_for_missing_product(db_session) -> None:
    user = User(telegram_id=111008, username="user", first_name="User", last_name="Eight")
    db_session.add(user)
    await db_session.commit()

    cart_item = await add_product_to_cart(db_session, user.telegram_id, 999)

    assert cart_item is None


@pytest.mark.asyncio
async def test_cart_persists_between_sessions(test_engine) -> None:
    session_factory = async_sessionmaker(
        bind=test_engine,
        expire_on_commit=False,
    )
    async with session_factory() as first_session:
        user = User(
            telegram_id=111009,
            username="user",
            first_name="User",
            last_name="Nine",
        )
        category = Category(name="Одежда")
        first_session.add_all([user, category])
        await first_session.flush()
        product = Product(category_id=category.id, name="Футболка", price=Decimal("100.00"))
        first_session.add(product)
        await first_session.commit()
        await add_product_to_cart(first_session, user.telegram_id, product.id)

    async with session_factory() as second_session:
        cart = await get_cart_by_telegram_id(second_session, 111009)

    assert cart is not None
    assert len(cart.items) == 1
