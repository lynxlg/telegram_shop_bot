from decimal import Decimal

import pytest
from sqlalchemy import select

from app.models.category import Category
from app.models.product import Product
from app.services.catalog_admin import (
    CategoryHasChildrenError,
    CategoryHasProductsError,
    NonLeafCategoryError,
    create_category,
    create_product,
    delete_category,
    delete_product,
    get_admin_products_by_category,
    parse_is_active,
    parse_price,
    set_product_active,
    update_category_name,
    update_product_description,
    update_product_image_url,
    update_product_name,
    update_product_price,
)


@pytest.mark.asyncio
async def test_create_and_rename_category(db_session) -> None:
    category = await create_category(db_session, "Одежда")
    assert category is not None
    assert category.parent_id is None

    updated_category = await update_category_name(db_session, category.id, "Одежда и обувь")
    assert updated_category is not None
    assert updated_category.name == "Одежда и обувь"


@pytest.mark.asyncio
async def test_create_subcategory_blocked_when_parent_has_products(db_session) -> None:
    parent = Category(name="Одежда")
    db_session.add(parent)
    await db_session.flush()
    db_session.add(
        Product(
            category_id=parent.id,
            name="Белая футболка",
            price=Decimal("1999.00"),
        )
    )
    await db_session.commit()

    with pytest.raises(CategoryHasProductsError):
        await create_category(db_session, "Футболки", parent_id=parent.id)


@pytest.mark.asyncio
async def test_delete_category_rejects_non_empty_category(db_session) -> None:
    parent = Category(name="Одежда")
    db_session.add(parent)
    await db_session.flush()
    child = Category(name="Футболки", parent_id=parent.id)
    db_session.add(child)
    await db_session.commit()

    with pytest.raises(CategoryHasChildrenError):
        await delete_category(db_session, parent.id)

    db_session.add(
        Product(
            category_id=child.id,
            name="Белая футболка",
            price=Decimal("1999.00"),
        )
    )
    await db_session.commit()

    with pytest.raises(CategoryHasProductsError):
        await delete_category(db_session, child.id)


@pytest.mark.asyncio
async def test_product_crud_flow_updates_existing_fields(db_session) -> None:
    category = Category(name="Футболки")
    db_session.add(category)
    await db_session.commit()

    product = await create_product(
        db_session,
        category_id=category.id,
        name="Белая футболка",
        price=parse_price("1999.00"),
        description="Базовая модель",
        image_url="https://example.com/tshirt.jpg",
        is_active=parse_is_active("да"),
    )
    assert product is not None

    await update_product_name(db_session, product.id, "Черная футболка")
    await update_product_price(db_session, product.id, parse_price("2499"))
    await update_product_description(db_session, product.id, "-")
    await update_product_image_url(db_session, product.id, "-")
    updated_product = await set_product_active(db_session, product.id, False)

    assert updated_product is not None
    assert updated_product.name == "Черная футболка"
    assert updated_product.price == Decimal("2499.00")
    assert updated_product.description is None
    assert updated_product.image_url is None
    assert updated_product.is_active is False

    products = await get_admin_products_by_category(db_session, category.id)
    assert [item.name for item in products] == ["Черная футболка"]

    deleted = await delete_product(db_session, product.id)
    assert deleted is True

    result = await db_session.execute(select(Product).where(Product.id == product.id))
    assert result.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_create_product_requires_leaf_category(db_session) -> None:
    parent = Category(name="Одежда")
    db_session.add(parent)
    await db_session.flush()
    db_session.add(Category(name="Футболки", parent_id=parent.id))
    await db_session.commit()

    with pytest.raises(NonLeafCategoryError):
        await create_product(
            db_session,
            category_id=parent.id,
            name="Белая футболка",
            price=parse_price("1999"),
            description=None,
            image_url=None,
            is_active=True,
        )
