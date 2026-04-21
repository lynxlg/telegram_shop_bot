from decimal import Decimal
from typing import List

from app.models.category import Category
from app.models.product import Product
from app.models.product_attribute import ProductAttribute
from app.ui_text import format_ui_text, get_ui_text

EMPTY_DESCRIPTION_TEXT = get_ui_text("catalog", "empty_description")
EMPTY_ATTRIBUTES_TEXT = get_ui_text("catalog", "empty_attributes")


def format_price(price: Decimal) -> str:
    return f"{price:.2f} ₽"


def build_categories_text(categories: List[Category]) -> str:
    lines = [get_ui_text("catalog", "categories_title")]
    lines.extend(category.name for category in categories)
    return "\n".join(lines)


def build_products_text(category: Category, products: List[Product]) -> str:
    lines = [category.name, "", get_ui_text("catalog", "products_title")]
    lines.extend(
        format_ui_text(
            "catalog",
            "product_list_item",
            name=product.name,
            price=format_price(product.price),
        )
        for product in products
    )
    return "\n".join(lines)


def build_product_text(product: Product, attributes: List[ProductAttribute]) -> str:
    description = product.description or EMPTY_DESCRIPTION_TEXT
    if attributes:
        attributes_text = "\n".join(
            f"{attribute.name}: {attribute.value}" for attribute in attributes
        )
    else:
        attributes_text = EMPTY_ATTRIBUTES_TEXT

    return "\n".join(
        [
            product.name,
            format_ui_text("catalog", "price_label", price=format_price(product.price)),
            "",
            format_ui_text("catalog", "description_label", description=description),
            "",
            get_ui_text("catalog", "attributes_title"),
            attributes_text,
        ]
    )
