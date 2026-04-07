from decimal import Decimal
from typing import List

from app.models.category import Category
from app.models.product import Product
from app.models.product_attribute import ProductAttribute


EMPTY_DESCRIPTION_TEXT = "Описание отсутствует."
EMPTY_ATTRIBUTES_TEXT = "Характеристики не указаны."


def format_price(price: Decimal) -> str:
    return f"{price:.2f} ₽"


def build_categories_text(categories: List[Category]) -> str:
    lines = ["Выберите раздел:"]
    lines.extend(category.name for category in categories)
    return "\n".join(lines)


def build_products_text(category: Category, products: List[Product]) -> str:
    lines = [f"{category.name}", "", "Товары:"]
    lines.extend(f"{product.name} - {format_price(product.price)}" for product in products)
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
            f"Цена: {format_price(product.price)}",
            "",
            f"Описание: {description}",
            "",
            "Характеристики:",
            attributes_text,
        ]
    )

