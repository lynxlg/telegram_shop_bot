from decimal import Decimal

import pytest

from app.models.category import Category
from app.models.product import Product
from app.models.product_attribute import ProductAttribute
from app.services.catalog import (
    get_active_products_by_category,
    get_category_by_id,
    get_child_categories,
    get_product_attributes,
    get_product_by_id,
    get_root_categories,
)


@pytest.mark.asyncio
async def test_get_root_categories_returns_only_root_sorted(db_session) -> None:
    category_b = Category(name="Бытовая техника")
    category_a = Category(name="Авто")
    child = Category(name="Шины", parent=category_a)
    db_session.add_all([category_b, category_a, child])
    await db_session.commit()

    categories = await get_root_categories(db_session)

    assert [category.name for category in categories] == ["Авто", "Бытовая техника"]


@pytest.mark.asyncio
async def test_get_category_by_id_returns_category(db_session) -> None:
    category = Category(name="Одежда")
    db_session.add(category)
    await db_session.commit()

    saved_category = await get_category_by_id(db_session, category.id)

    assert saved_category is not None
    assert saved_category.name == "Одежда"


@pytest.mark.asyncio
async def test_get_child_categories_returns_sorted_children(db_session) -> None:
    parent = Category(name="Одежда")
    db_session.add(parent)
    await db_session.flush()
    child_b = Category(name="Футболки", parent_id=parent.id)
    child_a = Category(name="Брюки", parent_id=parent.id)
    db_session.add_all([child_b, child_a])
    await db_session.commit()

    categories = await get_child_categories(db_session, parent.id)

    assert [category.name for category in categories] == ["Брюки", "Футболки"]


@pytest.mark.asyncio
async def test_get_child_categories_returns_empty_for_leaf(db_session) -> None:
    category = Category(name="Футболки")
    db_session.add(category)
    await db_session.commit()

    categories = await get_child_categories(db_session, category.id)

    assert categories == []


@pytest.mark.asyncio
async def test_get_active_products_by_category_filters_inactive(db_session) -> None:
    category = Category(name="Футболки")
    db_session.add(category)
    await db_session.flush()
    db_session.add_all(
        [
            Product(
                category_id=category.id,
                name="Белая футболка",
                price=Decimal("1999.00"),
                is_active=True,
            ),
            Product(
                category_id=category.id,
                name="Черная футболка",
                price=Decimal("1499.00"),
                is_active=False,
            ),
        ]
    )
    await db_session.commit()

    products = await get_active_products_by_category(db_session, category.id)

    assert [product.name for product in products] == ["Белая футболка"]


@pytest.mark.asyncio
async def test_get_product_by_id_returns_product(db_session) -> None:
    category = Category(name="Футболки")
    db_session.add(category)
    await db_session.flush()
    product = Product(
        category_id=category.id,
        name="Белая футболка",
        price=Decimal("1999.00"),
    )
    db_session.add(product)
    await db_session.commit()

    saved_product = await get_product_by_id(db_session, product.id)

    assert saved_product is not None
    assert saved_product.name == "Белая футболка"


@pytest.mark.asyncio
async def test_get_product_by_id_returns_image_url(db_session) -> None:
    category = Category(name="Футболки")
    db_session.add(category)
    await db_session.flush()
    product = Product(
        category_id=category.id,
        name="Белая футболка",
        price=Decimal("1999.00"),
        image_url="https://example.com/products/white-tshirt.jpg",
    )
    db_session.add(product)
    await db_session.commit()

    saved_product = await get_product_by_id(db_session, product.id)

    assert saved_product is not None
    assert saved_product.image_url == "https://example.com/products/white-tshirt.jpg"


@pytest.mark.asyncio
async def test_get_product_attributes_returns_sorted_attributes(db_session) -> None:
    category = Category(name="Футболки")
    db_session.add(category)
    await db_session.flush()
    product = Product(
        category_id=category.id,
        name="Белая футболка",
        price=Decimal("1999.00"),
    )
    db_session.add(product)
    await db_session.flush()
    db_session.add_all(
        [
            ProductAttribute(product_id=product.id, name="Размер", value="M"),
            ProductAttribute(product_id=product.id, name="Материал", value="Хлопок"),
        ]
    )
    await db_session.commit()

    attributes = await get_product_attributes(db_session, product.id)

    assert [attribute.name for attribute in attributes] == ["Материал", "Размер"]
