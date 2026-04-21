from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import select

from app.callbacks.admin_catalog import (
    DELETE_CATEGORY_ACTION,
    OPEN_PRODUCT_ACTION,
    AdminCatalogCallback,
)
from app.handlers.admin_catalog import (
    open_admin_catalog,
    open_admin_product,
    receive_category_name,
    receive_product_edit_value,
    receive_product_is_active,
    remove_category,
)
from app.models.category import Category
from app.models.product import Product
from app.models.user import User


@pytest.mark.asyncio
async def test_open_admin_catalog_denies_regular_user(db_session, message_factory) -> None:
    user = User(
        telegram_id=881001, username="buyer", first_name="Buyer", last_name="One", role="user"
    )
    db_session.add(user)
    await db_session.commit()
    message = message_factory(telegram_id=user.telegram_id, text_value="Админ каталог")

    await open_admin_catalog(message, db_session)

    message.answer.assert_awaited_once_with("У вас нет доступа к управлению каталогом.")


@pytest.mark.asyncio
async def test_open_admin_catalog_shows_root_categories_for_admin(
    db_session, message_factory
) -> None:
    admin = User(
        telegram_id=881002, username="admin", first_name="Админ", last_name="Один", role="admin"
    )
    db_session.add(admin)
    await db_session.flush()
    db_session.add_all([Category(name="Одежда"), Category(name="Обувь")])
    await db_session.commit()
    message = message_factory(
        telegram_id=admin.telegram_id,
        username="admin",
        first_name="Админ",
        text_value="Админ каталог",
    )

    await open_admin_catalog(message, db_session)

    assert "Админ каталог" in message.answer.await_args.args[0]
    assert "Одежда" in message.answer.await_args.args[0]
    assert "Обувь" in message.answer.await_args.args[0]


@pytest.mark.asyncio
async def test_receive_category_name_creates_root_category(db_session, message_factory) -> None:
    admin = User(
        telegram_id=881003, username="admin3", first_name="Админ", last_name="Три", role="admin"
    )
    db_session.add(admin)
    await db_session.commit()
    message = message_factory(
        telegram_id=admin.telegram_id, username="admin3", first_name="Админ", text_value="Новинки"
    )
    state = AsyncMock()
    state.get_data.return_value = {
        "mode": "create_category",
        "parent_category_id": None,
        "return_category_id": None,
    }

    await receive_category_name(message, state, db_session)

    result = await db_session.execute(select(Category).where(Category.name == "Новинки"))
    assert result.scalar_one() is not None
    assert message.answer.await_args_list[0].args[0] == "Раздел создан."
    assert "Админ каталог" in message.answer.await_args_list[1].args[0]


@pytest.mark.asyncio
async def test_receive_category_name_rejects_subcategory_when_parent_has_products(
    db_session, message_factory
) -> None:
    admin = User(
        telegram_id=881004, username="admin4", first_name="Админ", last_name="Четыре", role="admin"
    )
    parent = Category(name="Одежда")
    db_session.add_all([admin, parent])
    await db_session.flush()
    db_session.add(Product(category_id=parent.id, name="Белая футболка", price=Decimal("1999.00")))
    await db_session.commit()

    message = message_factory(
        telegram_id=admin.telegram_id, username="admin4", first_name="Админ", text_value="Футболки"
    )
    state = AsyncMock()
    state.get_data.side_effect = [
        {
            "mode": "create_category",
            "parent_category_id": parent.id,
            "return_category_id": parent.id,
        },
        {
            "mode": "create_category",
            "parent_category_id": parent.id,
            "return_category_id": parent.id,
        },
    ]

    await receive_category_name(message, state, db_session)

    result = await db_session.execute(select(Category).where(Category.parent_id == parent.id))
    assert result.scalar_one_or_none() is None
    assert (
        message.answer.await_args_list[0].args[0]
        == "Нельзя создать подраздел в разделе, где уже есть товары."
    )
    assert "Раздел: Одежда" in message.answer.await_args_list[1].args[0]


@pytest.mark.asyncio
async def test_receive_product_is_active_creates_product(db_session, message_factory) -> None:
    admin = User(
        telegram_id=881005, username="admin5", first_name="Админ", last_name="Пять", role="admin"
    )
    category = Category(name="Футболки")
    db_session.add_all([admin, category])
    await db_session.commit()

    message = message_factory(
        telegram_id=admin.telegram_id, username="admin5", first_name="Админ", text_value="да"
    )
    state = AsyncMock()
    state.get_data.return_value = {
        "category_id": category.id,
        "return_category_id": category.id,
        "product_name": "Белая футболка",
        "product_price": "1999.00",
        "product_description": "Летняя модель",
        "product_image_url": "https://example.com/tshirt.jpg",
    }

    await receive_product_is_active(message, state, db_session)

    result = await db_session.execute(select(Product).where(Product.category_id == category.id))
    product = result.scalar_one()
    assert product.name == "Белая футболка"
    assert product.is_active is True
    assert message.answer.await_args_list[0].args[0] == "Товар создан."
    assert "Раздел: Футболки" in message.answer.await_args_list[1].args[0]


@pytest.mark.asyncio
async def test_receive_product_edit_value_updates_name(db_session, message_factory) -> None:
    admin = User(
        telegram_id=881006, username="admin6", first_name="Админ", last_name="Шесть", role="admin"
    )
    category = Category(name="Футболки")
    db_session.add_all([admin, category])
    await db_session.flush()
    product = Product(category_id=category.id, name="Белая футболка", price=Decimal("1999.00"))
    db_session.add(product)
    await db_session.commit()

    message = message_factory(
        telegram_id=admin.telegram_id,
        username="admin6",
        first_name="Админ",
        text_value="Черная футболка",
    )
    state = AsyncMock()
    state.get_data.return_value = {
        "product_id": product.id,
        "field": "name",
        "return_product_id": product.id,
    }

    await receive_product_edit_value(message, state, db_session)

    result = await db_session.execute(select(Product).where(Product.id == product.id))
    updated_product = result.scalar_one()
    assert updated_product.name == "Черная футболка"
    assert message.answer.await_args_list[0].args[0] == "Товар обновлен."
    assert "Товар: Черная футболка" in message.answer.await_args_list[1].args[0]


@pytest.mark.asyncio
async def test_remove_category_rejects_category_with_products(db_session, callback_factory) -> None:
    admin = User(
        telegram_id=881007, username="admin7", first_name="Админ", last_name="Семь", role="admin"
    )
    category = Category(name="Футболки")
    db_session.add_all([admin, category])
    await db_session.flush()
    db_session.add(
        Product(category_id=category.id, name="Белая футболка", price=Decimal("1999.00"))
    )
    await db_session.commit()

    callback = callback_factory()
    callback.from_user = SimpleNamespace(id=admin.telegram_id)

    await remove_category(
        callback,
        AdminCatalogCallback(action=DELETE_CATEGORY_ACTION, category_id=category.id),
        db_session,
    )

    callback.answer.assert_awaited_once_with(
        "Нельзя удалить раздел, в котором есть товары.", show_alert=True
    )
    callback.message.edit_text.assert_not_called()


@pytest.mark.asyncio
async def test_open_admin_product_denies_non_admin_callback(db_session, callback_factory) -> None:
    user = User(
        telegram_id=881008, username="user8", first_name="Buyer", last_name="Eight", role="user"
    )
    category = Category(name="Футболки")
    db_session.add_all([user, category])
    await db_session.flush()
    product = Product(category_id=category.id, name="Белая футболка", price=Decimal("1999.00"))
    db_session.add(product)
    await db_session.commit()

    callback = callback_factory()
    callback.from_user = SimpleNamespace(id=user.telegram_id)

    await open_admin_product(
        callback,
        AdminCatalogCallback(action=OPEN_PRODUCT_ACTION, product_id=product.id),
        db_session,
    )

    callback.answer.assert_awaited_once_with(
        "У вас нет доступа к управлению каталогом.", show_alert=True
    )
