import logging
from decimal import Decimal, InvalidOperation
from typing import Optional

from sqlalchemy import Select, func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.category import Category
from app.models.product import Product

logger = logging.getLogger(__name__)

EMPTY_OPTIONAL_VALUE = "-"
YES_VALUES = {"да", "д", "yes", "y", "1", "true"}
NO_VALUES = {"нет", "н", "no", "n", "0", "false"}


class CatalogAdminValidationError(ValueError):
    pass


class EmptyRequiredFieldError(CatalogAdminValidationError):
    pass


class InvalidPriceError(CatalogAdminValidationError):
    pass


class InvalidBooleanValueError(CatalogAdminValidationError):
    pass


class CategoryHasChildrenError(CatalogAdminValidationError):
    pass


class CategoryHasProductsError(CatalogAdminValidationError):
    pass


class NonLeafCategoryError(CatalogAdminValidationError):
    pass


def normalize_required_text(value: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise EmptyRequiredFieldError("required text is empty")
    return normalized


def normalize_optional_text(value: str) -> Optional[str]:
    normalized = value.strip()
    if not normalized or normalized == EMPTY_OPTIONAL_VALUE:
        return None
    return normalized


def parse_price(value: str) -> Decimal:
    normalized = value.strip().replace(",", ".")
    try:
        price = Decimal(normalized)
    except InvalidOperation as exc:
        raise InvalidPriceError("invalid price") from exc

    if price <= 0:
        raise InvalidPriceError("price must be positive")

    return price.quantize(Decimal("0.01"))


def parse_is_active(value: str) -> bool:
    normalized = value.strip().lower()
    if normalized in YES_VALUES:
        return True
    if normalized in NO_VALUES:
        return False
    raise InvalidBooleanValueError("invalid boolean value")


async def get_admin_categories(session: AsyncSession, parent_id: Optional[int]) -> list[Category]:
    statement: Select[tuple[Category]] = (
        select(Category)
        .where(
            Category.parent_id.is_(None) if parent_id is None else Category.parent_id == parent_id
        )
        .order_by(Category.name.asc(), Category.id.asc())
    )
    result = await session.execute(statement)
    return list(result.scalars().all())


async def get_category_by_id(session: AsyncSession, category_id: int) -> Optional[Category]:
    result = await session.execute(select(Category).where(Category.id == category_id))
    return result.scalar_one_or_none()


async def get_admin_products_by_category(session: AsyncSession, category_id: int) -> list[Product]:
    statement: Select[tuple[Product]] = (
        select(Product)
        .where(Product.category_id == category_id)
        .order_by(Product.name.asc(), Product.id.asc())
    )
    result = await session.execute(statement)
    return list(result.scalars().all())


async def get_product_by_id(session: AsyncSession, product_id: int) -> Optional[Product]:
    result = await session.execute(select(Product).where(Product.id == product_id))
    return result.scalar_one_or_none()


async def _count_child_categories(session: AsyncSession, category_id: int) -> int:
    result = await session.execute(
        select(func.count()).select_from(Category).where(Category.parent_id == category_id)
    )
    return int(result.scalar_one())


async def _count_products(session: AsyncSession, category_id: int) -> int:
    result = await session.execute(
        select(func.count()).select_from(Product).where(Product.category_id == category_id)
    )
    return int(result.scalar_one())


async def create_category(
    session: AsyncSession,
    name: str,
    parent_id: Optional[int] = None,
) -> Optional[Category]:
    normalized_name = normalize_required_text(name)
    try:
        if parent_id is not None:
            parent_category = await get_category_by_id(session, parent_id)
            if parent_category is None:
                return None
            if await _count_products(session, parent_id):
                raise CategoryHasProductsError(
                    "cannot create child category under category with products"
                )

        category = Category(name=normalized_name, parent_id=parent_id)
        session.add(category)
        await session.commit()
        await session.refresh(category)
        return category
    except SQLAlchemyError:
        await session.rollback()
        logger.exception("Failed to create category parent_id=%s", parent_id)
        raise


async def update_category_name(
    session: AsyncSession,
    category_id: int,
    name: str,
) -> Optional[Category]:
    normalized_name = normalize_required_text(name)
    try:
        category = await get_category_by_id(session, category_id)
        if category is None:
            return None

        category.name = normalized_name
        await session.commit()
        await session.refresh(category)
        return category
    except SQLAlchemyError:
        await session.rollback()
        logger.exception("Failed to update category_id=%s", category_id)
        raise


async def delete_category(session: AsyncSession, category_id: int) -> bool:
    try:
        category = await get_category_by_id(session, category_id)
        if category is None:
            return False

        if await _count_child_categories(session, category_id):
            raise CategoryHasChildrenError("category has child categories")
        if await _count_products(session, category_id):
            raise CategoryHasProductsError("category has products")

        await session.delete(category)
        await session.commit()
        return True
    except SQLAlchemyError:
        await session.rollback()
        logger.exception("Failed to delete category_id=%s", category_id)
        raise


async def create_product(
    session: AsyncSession,
    category_id: int,
    name: str,
    price: Decimal,
    description: Optional[str],
    image_url: Optional[str],
    is_active: bool,
) -> Optional[Product]:
    normalized_name = normalize_required_text(name)
    normalized_description = normalize_optional_text(description or "")
    normalized_image_url = normalize_optional_text(image_url or "")
    try:
        category = await get_category_by_id(session, category_id)
        if category is None:
            return None
        if await _count_child_categories(session, category_id):
            raise NonLeafCategoryError("cannot create product in non-leaf category")

        product = Product(
            category_id=category_id,
            name=normalized_name,
            price=price,
            description=normalized_description,
            image_url=normalized_image_url,
            is_active=is_active,
        )
        session.add(product)
        await session.commit()
        await session.refresh(product)
        return product
    except SQLAlchemyError:
        await session.rollback()
        logger.exception("Failed to create product category_id=%s", category_id)
        raise


async def update_product_name(
    session: AsyncSession, product_id: int, name: str
) -> Optional[Product]:
    normalized_name = normalize_required_text(name)
    try:
        product = await get_product_by_id(session, product_id)
        if product is None:
            return None
        product.name = normalized_name
        await session.commit()
        await session.refresh(product)
        return product
    except SQLAlchemyError:
        await session.rollback()
        logger.exception("Failed to update product name product_id=%s", product_id)
        raise


async def update_product_price(
    session: AsyncSession, product_id: int, price: Decimal
) -> Optional[Product]:
    try:
        product = await get_product_by_id(session, product_id)
        if product is None:
            return None
        product.price = price
        await session.commit()
        await session.refresh(product)
        return product
    except SQLAlchemyError:
        await session.rollback()
        logger.exception("Failed to update product price product_id=%s", product_id)
        raise


async def update_product_description(
    session: AsyncSession,
    product_id: int,
    description: Optional[str],
) -> Optional[Product]:
    normalized_description = normalize_optional_text(description or "")
    try:
        product = await get_product_by_id(session, product_id)
        if product is None:
            return None
        product.description = normalized_description
        await session.commit()
        await session.refresh(product)
        return product
    except SQLAlchemyError:
        await session.rollback()
        logger.exception("Failed to update product description product_id=%s", product_id)
        raise


async def update_product_image_url(
    session: AsyncSession,
    product_id: int,
    image_url: Optional[str],
) -> Optional[Product]:
    normalized_image_url = normalize_optional_text(image_url or "")
    try:
        product = await get_product_by_id(session, product_id)
        if product is None:
            return None
        product.image_url = normalized_image_url
        await session.commit()
        await session.refresh(product)
        return product
    except SQLAlchemyError:
        await session.rollback()
        logger.exception("Failed to update product image_url product_id=%s", product_id)
        raise


async def set_product_active(
    session: AsyncSession, product_id: int, is_active: bool
) -> Optional[Product]:
    try:
        product = await get_product_by_id(session, product_id)
        if product is None:
            return None
        product.is_active = is_active
        await session.commit()
        await session.refresh(product)
        return product
    except SQLAlchemyError:
        await session.rollback()
        logger.exception("Failed to update product is_active product_id=%s", product_id)
        raise


async def delete_product(session: AsyncSession, product_id: int) -> bool:
    try:
        product = await get_product_by_id(session, product_id)
        if product is None:
            return False
        await session.delete(product)
        await session.commit()
        return True
    except SQLAlchemyError:
        await session.rollback()
        logger.exception("Failed to delete product_id=%s", product_id)
        raise
