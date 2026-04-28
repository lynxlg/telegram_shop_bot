import logging
from datetime import datetime, timezone
from typing import Optional

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery, InputMediaPhoto, Message
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.callbacks.catalog import (
    ADD_TO_CART_ACTION,
    GO_BACK_ACTION,
    OPEN_CATEGORY_ACTION,
    OPEN_PRODUCT_ACTION,
    CatalogCallback,
)
from app.keyboards.catalog import (
    build_child_categories_keyboard,
    build_product_keyboard,
    build_products_keyboard,
    build_root_categories_keyboard,
)
from app.models.category import Category
from app.models.user import User
from app.services.cart import add_product_to_cart
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
from app.ui_text import get_ui_text

logger = logging.getLogger(__name__)
router = Router()

CATALOG_EMPTY_TEXT = get_ui_text("catalog", "empty")
CATALOG_LOAD_ERROR_TEXT = get_ui_text("catalog", "load_error")
CATEGORY_NOT_FOUND_TEXT = get_ui_text("catalog", "category_not_found")
PRODUCT_NOT_FOUND_TEXT = get_ui_text("catalog", "product_not_found")
EMPTY_CATEGORY_PRODUCTS_TEXT = get_ui_text("catalog", "empty_category_products")
CART_UPDATE_ERROR_TEXT = get_ui_text("cart", "update_error")
CATALOG_BUTTON_TEXT = get_ui_text("main_menu", "catalog_button")
ADD_TO_CART_SUCCESS_TEXT = get_ui_text("catalog", "add_to_cart_success")
PRODUCTS_PER_PAGE = 5


async def _delete_message_safely(message) -> None:
    try:
        await message.delete()
    except Exception:
        logger.exception("Failed to delete catalog message during navigation")


async def _show_text_response(
    message,
    text: str,
    reply_markup=None,
) -> None:
    try:
        if reply_markup is None:
            await message.edit_text(text)
        else:
            await message.edit_text(text, reply_markup=reply_markup)
    except TelegramBadRequest:
        if reply_markup is None:
            await message.answer(text)
        else:
            await message.answer(text, reply_markup=reply_markup)
        await _delete_message_safely(message)


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
    page: int = 0,
) -> None:
    child_categories = await get_child_categories(db, category.id)
    if child_categories:
        await _show_text_response(
            message,
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
        await _show_text_response(
            message,
            EMPTY_CATEGORY_PRODUCTS_TEXT,
            reply_markup=build_child_categories_keyboard(
                categories=[],
                current_category_id=category.id,
                parent_category_id=category.parent_id,
            ),
        )
        return

    total_products = len(products)
    last_page = max((total_products - 1) // PRODUCTS_PER_PAGE, 0)
    current_page = min(max(page, 0), last_page)
    start = current_page * PRODUCTS_PER_PAGE
    end = start + PRODUCTS_PER_PAGE
    page_products = products[start:end]

    await _show_text_response(
        message,
        build_products_text(category, page_products),
        reply_markup=build_products_keyboard(
            products=page_products,
            category_id=category.id,
            parent_category_id=category.parent_id,
            page=current_page,
            has_previous_page=current_page > 0,
            has_next_page=end < total_products,
        ),
    )


async def _render_root_or_category(
    message,
    db: AsyncSession,
    category_id: Optional[int],
    page: int = 0,
) -> None:
    if category_id is None:
        categories = await get_root_categories(db)
        if not categories:
            await _show_text_response(message, CATALOG_EMPTY_TEXT)
            return

        await _show_text_response(
            message,
            build_categories_text(categories),
            reply_markup=build_root_categories_keyboard(categories),
        )
        return

    category = await get_category_by_id(db, category_id)
    if category is None:
        await _show_text_response(message, CATEGORY_NOT_FOUND_TEXT)
        return

    await _render_category_view(category, message, db, page=page)


async def _ensure_user_exists(callback: CallbackQuery, db: AsyncSession) -> None:
    telegram_user = callback.from_user
    result = await db.execute(select(User).where(User.telegram_id == telegram_user.id))
    user = result.scalar_one_or_none()
    now = datetime.now(timezone.utc)
    username = getattr(telegram_user, "username", None)
    first_name = getattr(telegram_user, "first_name", "Пользователь")
    last_name = getattr(telegram_user, "last_name", None)

    if user is None:
        user = User(
            telegram_id=telegram_user.id,
            username=username,
            first_name=first_name,
            last_name=last_name,
            role="user",
            last_activity=now,
        )
        db.add(user)
    else:
        user.username = username
        user.first_name = first_name
        user.last_name = last_name
        user.last_activity = now

    await db.commit()


@router.message(F.text == CATALOG_BUTTON_TEXT)
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

        await _render_category_view(
            category,
            callback.message,
            db,
            page=callback_data.page or 0,
        )
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
        product_text = build_product_text(product, attributes)
        reply_markup = build_product_keyboard(
            product_id=product.id,
            category_id=product.category_id,
            parent_category_id=callback_data.parent_category_id,
            page=callback_data.page or 0,
        )

        if product.image_url:
            try:
                await callback.message.edit_media(
                    media=InputMediaPhoto(
                        media=product.image_url,
                        caption=product_text,
                    ),
                    reply_markup=reply_markup,
                )
            except Exception:
                logger.exception(
                    "Failed to render product image for product_id=%s image_url=%s",
                    product.id,
                    product.image_url,
                )
                await _show_text_response(
                    callback.message,
                    product_text,
                    reply_markup=reply_markup,
                )
        else:
            await _show_text_response(
                callback.message,
                product_text,
                reply_markup=reply_markup,
            )
        await callback.answer()
    except SQLAlchemyError:
        logger.exception(
            "Database error while opening product_id=%s",
            callback_data.product_id,
        )
        await _show_text_response(callback.message, CATALOG_LOAD_ERROR_TEXT)
        await callback.answer()
    except Exception:
        logger.exception(
            "Unexpected error while rendering product_id=%s",
            callback_data.product_id,
        )
        await _show_text_response(callback.message, CATALOG_LOAD_ERROR_TEXT)
        await callback.answer()


@router.callback_query(CatalogCallback.filter(F.action == ADD_TO_CART_ACTION))
async def add_to_cart(
    callback: CallbackQuery,
    callback_data: CatalogCallback,
    db: AsyncSession,
) -> None:
    if callback_data.product_id is None:
        await callback.answer()
        return

    try:
        product = await get_product_by_id(db, callback_data.product_id)
        if product is None:
            await callback.answer(PRODUCT_NOT_FOUND_TEXT)
            return

        await _ensure_user_exists(callback, db)
        cart_item = await add_product_to_cart(
            db,
            callback.from_user.id,
            callback_data.product_id,
        )
        if cart_item is None:
            await callback.answer(CART_UPDATE_ERROR_TEXT)
            return

        await callback.answer(ADD_TO_CART_SUCCESS_TEXT)
    except SQLAlchemyError:
        logger.exception(
            "Database error while adding product_id=%s to cart for telegram_id=%s",
            callback_data.product_id,
            callback.from_user.id,
        )
        await callback.answer(CART_UPDATE_ERROR_TEXT)


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
        await _render_root_or_category(
            callback.message,
            db,
            callback_data.category_id,
            page=callback_data.page or 0,
        )
        await callback.answer()
    except SQLAlchemyError:
        logger.exception(
            "Database error while going back to category_id=%s",
            callback_data.category_id,
        )
        await _show_text_response(callback.message, CATALOG_LOAD_ERROR_TEXT)
        await callback.answer()
