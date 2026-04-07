from decimal import Decimal
from unittest.mock import AsyncMock

import pytest
from sqlalchemy.exc import SQLAlchemyError

from app.callbacks.catalog import (
    CatalogCallback,
    GO_BACK_ACTION,
    OPEN_CATEGORY_ACTION,
    OPEN_PRODUCT_ACTION,
)
from app.handlers import catalog as catalog_module
from app.handlers.catalog import go_back, open_catalog, open_category, open_product
from app.models.category import Category
from app.models.product import Product
from app.models.product_attribute import ProductAttribute


@pytest.mark.asyncio
async def test_open_catalog_shows_root_categories(db_session, message_factory) -> None:
    db_session.add_all([Category(name="Одежда"), Category(name="Техника")])
    await db_session.commit()
    message = message_factory(text_value="Каталог")

    await open_catalog(message, db_session)

    message.answer.assert_awaited_once()
    assert "Выберите раздел:" in message.answer.await_args.args[0]
    reply_markup = message.answer.await_args.kwargs["reply_markup"]
    assert [button.text for row in reply_markup.inline_keyboard for button in row] == [
        "Одежда",
        "Техника",
    ]


@pytest.mark.asyncio
async def test_open_catalog_handles_empty_catalog(db_session, message_factory) -> None:
    message = message_factory(text_value="Каталог")

    await open_catalog(message, db_session)

    message.answer.assert_awaited_once_with("Каталог пока пуст.")


@pytest.mark.asyncio
async def test_open_category_shows_child_categories(db_session, callback_factory) -> None:
    parent = Category(name="Одежда")
    db_session.add(parent)
    await db_session.flush()
    db_session.add_all(
        [
            Category(name="Брюки", parent_id=parent.id),
            Category(name="Футболки", parent_id=parent.id),
        ]
    )
    await db_session.commit()
    callback = callback_factory()
    callback_data = CatalogCallback(action=OPEN_CATEGORY_ACTION, category_id=parent.id)

    await open_category(callback, callback_data, db_session)

    callback.message.edit_text.assert_awaited_once()
    assert "Выберите раздел:" in callback.message.edit_text.await_args.args[0]
    reply_markup = callback.message.edit_text.await_args.kwargs["reply_markup"]
    assert [button.text for row in reply_markup.inline_keyboard for button in row] == [
        "Брюки",
        "Футболки",
        "Назад",
    ]


@pytest.mark.asyncio
async def test_open_category_shows_products_for_leaf_category(db_session, callback_factory) -> None:
    category = Category(name="Футболки")
    db_session.add(category)
    await db_session.flush()
    db_session.add(
        Product(
            category_id=category.id,
            name="Белая футболка",
            price=Decimal("1999.00"),
            is_active=True,
        )
    )
    await db_session.commit()
    callback = callback_factory()
    callback_data = CatalogCallback(action=OPEN_CATEGORY_ACTION, category_id=category.id)

    await open_category(callback, callback_data, db_session)

    callback.message.edit_text.assert_awaited_once()
    assert "Белая футболка - 1999.00 ₽" in callback.message.edit_text.await_args.args[0]


@pytest.mark.asyncio
async def test_open_category_handles_leaf_without_products(db_session, callback_factory) -> None:
    category = Category(name="Футболки")
    db_session.add(category)
    await db_session.commit()
    callback = callback_factory()
    callback_data = CatalogCallback(action=OPEN_CATEGORY_ACTION, category_id=category.id)

    await open_category(callback, callback_data, db_session)

    callback.message.edit_text.assert_awaited_once()
    assert callback.message.edit_text.await_args.args[0] == "В этом разделе пока нет товаров."


@pytest.mark.asyncio
async def test_open_product_shows_product_card(db_session, callback_factory) -> None:
    category = Category(name="Футболки")
    db_session.add(category)
    await db_session.flush()
    product = Product(
        category_id=category.id,
        name="Белая футболка",
        price=Decimal("1999.00"),
        description="Базовая модель",
    )
    db_session.add(product)
    await db_session.flush()
    db_session.add(ProductAttribute(product_id=product.id, name="Размер", value="M"))
    await db_session.commit()
    callback = callback_factory()
    callback_data = CatalogCallback(
        action=OPEN_PRODUCT_ACTION,
        product_id=product.id,
        parent_category_id=None,
    )

    await open_product(callback, callback_data, db_session)

    callback.message.edit_text.assert_awaited_once()
    text = callback.message.edit_text.await_args.args[0]
    assert "Белая футболка" in text
    assert "Цена: 1999.00 ₽" in text
    assert "Описание: Базовая модель" in text
    assert "Размер: M" in text


@pytest.mark.asyncio
async def test_open_product_uses_description_fallback(db_session, callback_factory) -> None:
    category = Category(name="Футболки")
    db_session.add(category)
    await db_session.flush()
    product = Product(
        category_id=category.id,
        name="Белая футболка",
        price=Decimal("1999.00"),
        description=None,
    )
    db_session.add(product)
    await db_session.commit()
    callback = callback_factory()
    callback_data = CatalogCallback(
        action=OPEN_PRODUCT_ACTION,
        product_id=product.id,
        parent_category_id=None,
    )

    await open_product(callback, callback_data, db_session)

    assert "Описание отсутствует." in callback.message.edit_text.await_args.args[0]


@pytest.mark.asyncio
async def test_open_product_uses_attributes_fallback(db_session, callback_factory) -> None:
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
    callback = callback_factory()
    callback_data = CatalogCallback(
        action=OPEN_PRODUCT_ACTION,
        product_id=product.id,
        parent_category_id=None,
    )

    await open_product(callback, callback_data, db_session)

    assert "Характеристики не указаны." in callback.message.edit_text.await_args.args[0]


@pytest.mark.asyncio
async def test_go_back_returns_to_parent_category_level(db_session, callback_factory) -> None:
    parent = Category(name="Одежда")
    db_session.add(parent)
    await db_session.flush()
    db_session.add(Category(name="Футболки", parent_id=parent.id))
    await db_session.commit()
    callback = callback_factory()
    callback_data = CatalogCallback(action=GO_BACK_ACTION, category_id=parent.id)

    await go_back(callback, callback_data, db_session)

    callback.message.edit_text.assert_awaited_once()
    assert "Выберите раздел:" in callback.message.edit_text.await_args.args[0]
    assert "Футболки" in callback.message.edit_text.await_args.args[0]


@pytest.mark.asyncio
async def test_open_category_handles_missing_category(db_session, callback_factory) -> None:
    callback = callback_factory()
    callback_data = CatalogCallback(action=OPEN_CATEGORY_ACTION, category_id=999)

    await open_category(callback, callback_data, db_session)

    callback.message.edit_text.assert_awaited_once_with("Раздел не найден.")


@pytest.mark.asyncio
async def test_open_product_handles_missing_product(db_session, callback_factory) -> None:
    callback = callback_factory()
    callback_data = CatalogCallback(action=OPEN_PRODUCT_ACTION, product_id=999)

    await open_product(callback, callback_data, db_session)

    callback.message.edit_text.assert_awaited_once_with("Товар не найден.")


@pytest.mark.asyncio
async def test_open_catalog_handles_database_error(message_factory, monkeypatch) -> None:
    message = message_factory(text_value="Каталог")

    async def broken_get_root_categories(_session):
        raise SQLAlchemyError("boom")

    monkeypatch.setattr(catalog_module, "get_root_categories", broken_get_root_categories)

    await open_catalog(message, AsyncMock())

    message.answer.assert_awaited_once_with("Не удалось загрузить каталог. Попробуйте позже.")
