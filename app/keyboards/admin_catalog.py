from typing import Optional

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.callbacks.admin_catalog import (
    BACK_TO_CATEGORY_ACTION,
    BACK_TO_ROOT_ACTION,
    DELETE_CATEGORY_ACTION,
    DELETE_PRODUCT_ACTION,
    OPEN_CATEGORY_ACTION,
    OPEN_PRODUCT_ACTION,
    START_CREATE_CATEGORY_ACTION,
    START_CREATE_PRODUCT_ACTION,
    START_EDIT_CATEGORY_ACTION,
    START_EDIT_PRODUCT_ACTION,
    TOGGLE_PRODUCT_ACTIVE_ACTION,
    AdminCatalogCallback,
)
from app.models.category import Category
from app.models.product import Product
from app.services.catalog_text import format_price
from app.ui_text import format_ui_text, get_ui_text

CREATE_CATEGORY_BUTTON_TEXT = get_ui_text("admin_catalog", "create_category_button")
EDIT_CATEGORY_BUTTON_TEXT = get_ui_text("admin_catalog", "edit_category_button")
DELETE_CATEGORY_BUTTON_TEXT = get_ui_text("admin_catalog", "delete_category_button")
CREATE_PRODUCT_BUTTON_TEXT = get_ui_text("admin_catalog", "create_product_button")
EDIT_NAME_BUTTON_TEXT = get_ui_text("admin_catalog", "edit_name_button")
EDIT_PRICE_BUTTON_TEXT = get_ui_text("admin_catalog", "edit_price_button")
EDIT_DESCRIPTION_BUTTON_TEXT = get_ui_text("admin_catalog", "edit_description_button")
EDIT_IMAGE_URL_BUTTON_TEXT = get_ui_text("admin_catalog", "edit_image_url_button")
DELETE_PRODUCT_BUTTON_TEXT = get_ui_text("admin_catalog", "delete_product_button")
BACK_TO_ROOT_BUTTON_TEXT = get_ui_text("admin_catalog", "back_to_root_button")
BACK_TO_CATEGORY_BUTTON_TEXT = get_ui_text("admin_catalog", "back_to_category_button")
TOGGLE_PRODUCT_ON_BUTTON_TEXT = get_ui_text("admin_catalog", "toggle_product_on_button")
TOGGLE_PRODUCT_OFF_BUTTON_TEXT = get_ui_text("admin_catalog", "toggle_product_off_button")


def build_admin_category_keyboard(
    categories: list[Category],
    products: list[Product],
    current_category_id: Optional[int],
    parent_category_id: Optional[int],
    can_add_product: bool,
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    for category in categories:
        builder.button(
            text=category.name,
            callback_data=AdminCatalogCallback(
                action=OPEN_CATEGORY_ACTION,
                category_id=category.id,
            ),
        )

    for product in products:
        builder.button(
            text=format_ui_text(
                "catalog",
                "product_button",
                name=product.name,
                price=format_price(product.price),
            ),
            callback_data=AdminCatalogCallback(
                action=OPEN_PRODUCT_ACTION,
                product_id=product.id,
                category_id=current_category_id,
            ),
        )

    builder.button(
        text=CREATE_CATEGORY_BUTTON_TEXT,
        callback_data=AdminCatalogCallback(
            action=START_CREATE_CATEGORY_ACTION,
            category_id=current_category_id,
        ),
    )

    if current_category_id is not None:
        builder.button(
            text=EDIT_CATEGORY_BUTTON_TEXT,
            callback_data=AdminCatalogCallback(
                action=START_EDIT_CATEGORY_ACTION,
                category_id=current_category_id,
            ),
        )
        builder.button(
            text=DELETE_CATEGORY_BUTTON_TEXT,
            callback_data=AdminCatalogCallback(
                action=DELETE_CATEGORY_ACTION,
                category_id=current_category_id,
            ),
        )

    if current_category_id is not None and can_add_product:
        builder.button(
            text=CREATE_PRODUCT_BUTTON_TEXT,
            callback_data=AdminCatalogCallback(
                action=START_CREATE_PRODUCT_ACTION,
                category_id=current_category_id,
            ),
        )

    if current_category_id is not None:
        if parent_category_id is None:
            builder.button(
                text=BACK_TO_ROOT_BUTTON_TEXT,
                callback_data=AdminCatalogCallback(action=BACK_TO_ROOT_ACTION),
            )
        else:
            builder.button(
                text=BACK_TO_CATEGORY_BUTTON_TEXT,
                callback_data=AdminCatalogCallback(
                    action=OPEN_CATEGORY_ACTION,
                    category_id=parent_category_id,
                ),
            )

    builder.adjust(1)
    return builder.as_markup()


def build_admin_product_keyboard(
    product_id: int, category_id: int, is_active: bool
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(
        text=EDIT_NAME_BUTTON_TEXT,
        callback_data=AdminCatalogCallback(
            action=START_EDIT_PRODUCT_ACTION,
            product_id=product_id,
            field="name",
        ),
    )
    builder.button(
        text=EDIT_PRICE_BUTTON_TEXT,
        callback_data=AdminCatalogCallback(
            action=START_EDIT_PRODUCT_ACTION,
            product_id=product_id,
            field="price",
        ),
    )
    builder.button(
        text=EDIT_DESCRIPTION_BUTTON_TEXT,
        callback_data=AdminCatalogCallback(
            action=START_EDIT_PRODUCT_ACTION,
            product_id=product_id,
            field="description",
        ),
    )
    builder.button(
        text=EDIT_IMAGE_URL_BUTTON_TEXT,
        callback_data=AdminCatalogCallback(
            action=START_EDIT_PRODUCT_ACTION,
            product_id=product_id,
            field="image_url",
        ),
    )
    builder.button(
        text=TOGGLE_PRODUCT_OFF_BUTTON_TEXT if is_active else TOGGLE_PRODUCT_ON_BUTTON_TEXT,
        callback_data=AdminCatalogCallback(
            action=TOGGLE_PRODUCT_ACTIVE_ACTION,
            product_id=product_id,
        ),
    )
    builder.button(
        text=DELETE_PRODUCT_BUTTON_TEXT,
        callback_data=AdminCatalogCallback(
            action=DELETE_PRODUCT_ACTION,
            product_id=product_id,
            category_id=category_id,
        ),
    )
    builder.button(
        text=BACK_TO_CATEGORY_BUTTON_TEXT,
        callback_data=AdminCatalogCallback(
            action=BACK_TO_CATEGORY_ACTION,
            category_id=category_id,
        ),
    )
    builder.adjust(2, 2, 1, 1, 1)
    return builder.as_markup()
