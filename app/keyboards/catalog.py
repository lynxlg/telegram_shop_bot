from typing import List, Optional

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.callbacks.catalog import (
    ADD_TO_CART_ACTION,
    GO_BACK_ACTION,
    OPEN_CATEGORY_ACTION,
    OPEN_PRODUCT_ACTION,
    CatalogCallback,
)
from app.models.category import Category
from app.models.product import Product
from app.ui_text import format_ui_text, get_ui_text

BACK_BUTTON_TEXT = get_ui_text("catalog", "back_button")
ADD_TO_CART_BUTTON_TEXT = get_ui_text("catalog", "add_to_cart_button")


def build_root_categories_keyboard(categories: List[Category]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for category in categories:
        builder.button(
            text=category.name,
            callback_data=CatalogCallback(
                action=OPEN_CATEGORY_ACTION,
                category_id=category.id,
                parent_category_id=None,
            ),
        )
    builder.adjust(1)
    return builder.as_markup()


def build_child_categories_keyboard(
    categories: List[Category],
    current_category_id: int,
    parent_category_id: Optional[int],
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for category in categories:
        builder.button(
            text=category.name,
            callback_data=CatalogCallback(
                action=OPEN_CATEGORY_ACTION,
                category_id=category.id,
                parent_category_id=current_category_id,
            ),
        )
    builder.button(
        text=BACK_BUTTON_TEXT,
        callback_data=CatalogCallback(
            action=GO_BACK_ACTION,
            category_id=parent_category_id,
        ),
    )
    builder.adjust(1)
    return builder.as_markup()


def build_products_keyboard(
    products: List[Product],
    category_id: int,
    parent_category_id: Optional[int],
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for product in products:
        builder.button(
            text=format_ui_text(
                "catalog",
                "product_button",
                name=product.name,
                price=f"{product.price:.2f} ₽",
            ),
            callback_data=CatalogCallback(
                action=OPEN_PRODUCT_ACTION,
                product_id=product.id,
                category_id=category_id,
                parent_category_id=parent_category_id,
            ),
        )
    builder.button(
        text=BACK_BUTTON_TEXT,
        callback_data=CatalogCallback(
            action=GO_BACK_ACTION,
            category_id=parent_category_id,
        ),
    )
    builder.adjust(1)
    return builder.as_markup()


def build_product_keyboard(
    product_id: int,
    category_id: int,
    parent_category_id: Optional[int],
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(
        text=ADD_TO_CART_BUTTON_TEXT,
        callback_data=CatalogCallback(
            action=ADD_TO_CART_ACTION,
            product_id=product_id,
            category_id=category_id,
            parent_category_id=parent_category_id,
        ),
    )
    builder.button(
        text=BACK_BUTTON_TEXT,
        callback_data=CatalogCallback(
            action=GO_BACK_ACTION,
            category_id=category_id,
            parent_category_id=parent_category_id,
        ),
    )
    builder.adjust(1)
    return builder.as_markup()
