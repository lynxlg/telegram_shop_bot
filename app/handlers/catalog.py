import logging
from typing import Optional

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.callbacks.catalog import (
    CatalogCallback,
    GO_BACK_ACTION,
    OPEN_CATEGORY_ACTION,
    OPEN_PRODUCT_ACTION,
)
from app.keyboards.catalog import (
    build_child_categories_keyboard,
    build_product_keyboard,
    build_products_keyboard,
    build_root_categories_keyboard,
)
from app.models.category import Category
from app.services.catalog import (
    get_active_products_by_category,
    get_category_by_id,
    get_child_categories,
    get_product_attributes,
    get_product_by_id,
    get_root_categories,
)
from app.services.catalog_text import (
    build_categories_text,
    build_product_text,
    build_products_text,
)


logger = logging.getLogger(__name__)
router = Router()

CATALOG_EMPTY_TEXT = "Каталог пока пуст."
CATALOG_LOAD_ERROR_TEXT = "Не удалось загрузить каталог. Попробуйте позже."
CATEGORY_NOT_FOUND_TEXT = "Раздел не найден."
PRODUCT_NOT_FOUND_TEXT = "Товар не найден."
EMPTY_CATEGORY_PRODUCTS_TEXT = "В этом разделе пока нет товаров."


async def _show_root_catalog(message: Message, db: AsyncSession) -> None:
    categories = await get_root_categories(db)
    if not categories:
        await message.answer(CATALOG_EMPTY_TEXT)
        return

    await message.answer(
        build_categories_text(categories),
        reply_markup=build_root_categories_keyboard(categories),
    )


async def _render_category_view(
    category: Category,
    message,
    db: AsyncSession,
) -> None:
    child_categories = await get_child_categories(db, category.id)
    if child_categories:
        await message.edit_text(
            build_categories_text(child_categories),
            reply_markup=build_child_categories_keyboard(
                categories=child_categories,
                current_category_id=category.id,
                parent_category_id=category.parent_id,
            ),
        )
        return

    products = await get_active_products_by_category(db, category.id)
    if not products:
        await message.edit_text(
            EMPTY_CATEGORY_PRODUCTS_TEXT,
            reply_markup=build_child_categories_keyboard(
                categories=[],
                current_category_id=category.id,
                parent_category_id=category.parent_id,
            ),
        )
        return

    await message.edit_text(
        build_products_text(category, products),
        reply_markup=build_products_keyboard(
            products=products,
            category_id=category.id,
            parent_category_id=category.parent_id,
        ),
    )


async def _render_root_or_category(
    message,
    db: AsyncSession,
    category_id: Optional[int],
) -> None:
    if category_id is None:
        categories = await get_root_categories(db)
        if not categories:
            await message.edit_text(CATALOG_EMPTY_TEXT)
            return

        await message.edit_text(
            build_categories_text(categories),
            reply_markup=build_root_categories_keyboard(categories),
        )
        return

    category = await get_category_by_id(db, category_id)
    if category is None:
        await message.edit_text(CATEGORY_NOT_FOUND_TEXT)
        return

    await _render_category_view(category, message, db)


@router.message(F.text == "Каталог")
async def open_catalog(message: Message, db: AsyncSession) -> None:
    try:
        await _show_root_catalog(message, db)
    except SQLAlchemyError:
        logger.exception("Database error while opening root catalog")
        await message.answer(CATALOG_LOAD_ERROR_TEXT)


@router.callback_query(CatalogCallback.filter(F.action == OPEN_CATEGORY_ACTION))
async def open_category(
    callback: CallbackQuery,
    callback_data: CatalogCallback,
    db: AsyncSession,
) -> None:
    if callback.message is None or callback_data.category_id is None:
        await callback.answer()
        return

    try:
        category = await get_category_by_id(db, callback_data.category_id)
        if category is None:
            await callback.message.edit_text(CATEGORY_NOT_FOUND_TEXT)
            await callback.answer()
            return

        await _render_category_view(category, callback.message, db)
        await callback.answer()
    except SQLAlchemyError:
        logger.exception(
            "Database error while opening category_id=%s",
            callback_data.category_id,
        )
        await callback.message.edit_text(CATALOG_LOAD_ERROR_TEXT)
        await callback.answer()


@router.callback_query(CatalogCallback.filter(F.action == OPEN_PRODUCT_ACTION))
async def open_product(
    callback: CallbackQuery,
    callback_data: CatalogCallback,
    db: AsyncSession,
) -> None:
    if callback.message is None or callback_data.product_id is None:
        await callback.answer()
        return

    try:
        product = await get_product_by_id(db, callback_data.product_id)
        if product is None:
            await callback.message.edit_text(PRODUCT_NOT_FOUND_TEXT)
            await callback.answer()
            return

        attributes = await get_product_attributes(db, product.id)
        await callback.message.edit_text(
            build_product_text(product, attributes),
            reply_markup=build_product_keyboard(
                category_id=product.category_id,
                parent_category_id=callback_data.parent_category_id,
            ),
        )
        await callback.answer()
    except SQLAlchemyError:
        logger.exception(
            "Database error while opening product_id=%s",
            callback_data.product_id,
        )
        await callback.message.edit_text(CATALOG_LOAD_ERROR_TEXT)
        await callback.answer()


@router.callback_query(CatalogCallback.filter(F.action == GO_BACK_ACTION))
async def go_back(
    callback: CallbackQuery,
    callback_data: CatalogCallback,
    db: AsyncSession,
) -> None:
    if callback.message is None:
        await callback.answer()
        return

    try:
        await _render_root_or_category(callback.message, db, callback_data.category_id)
        await callback.answer()
    except SQLAlchemyError:
        logger.exception(
            "Database error while going back to category_id=%s",
            callback_data.category_id,
        )
        await callback.message.edit_text(CATALOG_LOAD_ERROR_TEXT)
        await callback.answer()

