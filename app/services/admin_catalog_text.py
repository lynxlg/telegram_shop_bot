from app.models.category import Category
from app.models.product import Product
from app.services.catalog_text import format_price
from app.ui_text import format_ui_text, get_ui_text

ADMIN_ROOT_TITLE = get_ui_text("admin_catalog", "root_title")
ADMIN_CATEGORY_TITLE = get_ui_text("admin_catalog", "category_title")
ADMIN_SUBCATEGORIES_TITLE = get_ui_text("admin_catalog", "subcategories_title")
ADMIN_PRODUCTS_TITLE = get_ui_text("admin_catalog", "products_title")
ADMIN_EMPTY_CATEGORIES = get_ui_text("admin_catalog", "empty_categories")
ADMIN_EMPTY_PRODUCTS = get_ui_text("admin_catalog", "empty_products")
ADMIN_EMPTY_DESCRIPTION = get_ui_text("admin_catalog", "empty_description")
ADMIN_EMPTY_IMAGE_URL = get_ui_text("admin_catalog", "empty_image_url")
ADMIN_LEAF_HINT = get_ui_text("admin_catalog", "leaf_hint")
ADMIN_NON_LEAF_HINT = get_ui_text("admin_catalog", "non_leaf_hint")
ADMIN_ACTIVITY_ACTIVE = get_ui_text("admin_catalog", "activity_active")
ADMIN_ACTIVITY_INACTIVE = get_ui_text("admin_catalog", "activity_inactive")


def get_product_activity_label(is_active: bool) -> str:
    return ADMIN_ACTIVITY_ACTIVE if is_active else ADMIN_ACTIVITY_INACTIVE


def format_admin_root_text(categories: list[Category]) -> str:
    lines = [ADMIN_ROOT_TITLE, "", ADMIN_SUBCATEGORIES_TITLE]
    if not categories:
        lines.append(ADMIN_EMPTY_CATEGORIES)
        return "\n".join(lines)

    lines.extend(
        format_ui_text("admin_catalog", "category_item", index=index, name=category.name)
        for index, category in enumerate(categories, start=1)
    )
    return "\n".join(lines)


def format_admin_category_text(
    category: Category,
    child_categories: list[Category],
    products: list[Product],
    can_add_product: bool,
) -> str:
    lines = [format_ui_text("admin_catalog", "category_title", category_name=category.name), ""]
    lines.append(ADMIN_SUBCATEGORIES_TITLE)
    if child_categories:
        lines.extend(
            format_ui_text("admin_catalog", "category_item", index=index, name=item.name)
            for index, item in enumerate(child_categories, start=1)
        )
    else:
        lines.append(ADMIN_EMPTY_CATEGORIES)

    lines.extend(["", ADMIN_PRODUCTS_TITLE])
    if products:
        lines.extend(
            format_ui_text(
                "admin_catalog",
                "product_item",
                index=index,
                name=product.name,
                price=format_price(product.price),
                activity=get_product_activity_label(product.is_active),
            )
            for index, product in enumerate(products, start=1)
        )
    else:
        lines.append(ADMIN_EMPTY_PRODUCTS)

    lines.extend(["", ADMIN_LEAF_HINT if can_add_product else ADMIN_NON_LEAF_HINT])
    return "\n".join(lines)


def format_admin_product_text(product: Product) -> str:
    description = product.description or ADMIN_EMPTY_DESCRIPTION
    image_url = product.image_url or ADMIN_EMPTY_IMAGE_URL
    return format_ui_text(
        "admin_catalog",
        "product_details",
        name=product.name,
        price=format_price(product.price),
        activity=get_product_activity_label(product.is_active),
        description=description,
        image_url=image_url,
    )
