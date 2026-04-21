import logging
from typing import List, Optional

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.category import Category
from app.models.product import Product
from app.models.product_attribute import ProductAttribute

logger = logging.getLogger(__name__)


async def get_root_categories(session: AsyncSession) -> List[Category]:
    statement: Select[tuple[Category]] = (
        select(Category).where(Category.parent_id.is_(None)).order_by(Category.name.asc())
    )
    result = await session.execute(statement)
    return list(result.scalars().all())


async def get_category_by_id(session: AsyncSession, category_id: int) -> Optional[Category]:
    statement: Select[tuple[Category]] = select(Category).where(Category.id == category_id)
    result = await session.execute(statement)
    return result.scalar_one_or_none()


async def get_child_categories(session: AsyncSession, category_id: int) -> List[Category]:
    statement: Select[tuple[Category]] = (
        select(Category).where(Category.parent_id == category_id).order_by(Category.name.asc())
    )
    result = await session.execute(statement)
    return list(result.scalars().all())


async def get_active_products_by_category(session: AsyncSession, category_id: int) -> List[Product]:
    statement: Select[tuple[Product]] = (
        select(Product)
        .where(Product.category_id == category_id, Product.is_active.is_(True))
        .order_by(Product.name.asc())
    )
    result = await session.execute(statement)
    return list(result.scalars().all())


async def get_product_by_id(session: AsyncSession, product_id: int) -> Optional[Product]:
    statement: Select[tuple[Product]] = select(Product).where(Product.id == product_id)
    result = await session.execute(statement)
    return result.scalar_one_or_none()


async def get_product_attributes(session: AsyncSession, product_id: int) -> List[ProductAttribute]:
    statement: Select[tuple[ProductAttribute]] = (
        select(ProductAttribute)
        .where(ProductAttribute.product_id == product_id)
        .order_by(ProductAttribute.name.asc(), ProductAttribute.id.asc())
    )
    result = await session.execute(statement)
    return list(result.scalars().all())
