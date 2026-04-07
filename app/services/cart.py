import logging
from typing import Optional

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.cart import Cart
from app.models.cart_item import CartItem
from app.models.product import Product
from app.models.user import User


logger = logging.getLogger(__name__)


async def get_or_create_cart_by_telegram_id(
    session: AsyncSession,
    telegram_id: int,
) -> Optional[Cart]:
    try:
        result = await session.execute(select(User).where(User.telegram_id == telegram_id))
        user = result.scalar_one_or_none()
        if user is None:
            return None

        cart_result = await session.execute(
            select(Cart)
            .options(selectinload(Cart.items))
            .where(Cart.user_id == user.id)
        )
        cart = cart_result.scalar_one_or_none()
        if cart is not None:
            return cart

        cart = Cart(user_id=user.id)
        session.add(cart)
        await session.flush()
        await session.refresh(cart)
        return cart
    except SQLAlchemyError:
        logger.exception("Failed to get or create cart for telegram_id=%s", telegram_id)
        raise


async def add_product_to_cart(
    session: AsyncSession,
    telegram_id: int,
    product_id: int,
) -> Optional[CartItem]:
    try:
        product_result = await session.execute(
            select(Product).where(Product.id == product_id)
        )
        product = product_result.scalar_one_or_none()
        if product is None:
            return None

        cart = await get_or_create_cart_by_telegram_id(session, telegram_id)
        if cart is None:
            return None

        item_result = await session.execute(
            select(CartItem).where(
                CartItem.cart_id == cart.id,
                CartItem.product_id == product_id,
            )
        )
        cart_item = item_result.scalar_one_or_none()

        if cart_item is None:
            cart_item = CartItem(cart_id=cart.id, product_id=product_id, quantity=1)
            session.add(cart_item)
        else:
            cart_item.quantity += 1

        await session.commit()
        await session.refresh(cart_item)
        return cart_item
    except SQLAlchemyError:
        await session.rollback()
        logger.exception(
            "Failed to add product_id=%s to cart for telegram_id=%s",
            product_id,
            telegram_id,
        )
        raise


async def get_cart_by_telegram_id(
    session: AsyncSession,
    telegram_id: int,
) -> Optional[Cart]:
    try:
        result = await session.execute(select(User).where(User.telegram_id == telegram_id))
        user = result.scalar_one_or_none()
        if user is None:
            return None

        cart_result = await session.execute(
            select(Cart)
            .options(selectinload(Cart.items).selectinload(CartItem.product))
            .where(Cart.user_id == user.id)
        )
        return cart_result.scalar_one_or_none()
    except SQLAlchemyError:
        logger.exception("Failed to load cart for telegram_id=%s", telegram_id)
        raise


async def increase_cart_item_quantity(
    session: AsyncSession,
    cart_item_id: int,
) -> Optional[CartItem]:
    try:
        result = await session.execute(select(CartItem).where(CartItem.id == cart_item_id))
        cart_item = result.scalar_one_or_none()
        if cart_item is None:
            return None

        cart_item.quantity += 1
        await session.commit()
        await session.refresh(cart_item)
        return cart_item
    except SQLAlchemyError:
        await session.rollback()
        logger.exception("Failed to increase cart_item_id=%s", cart_item_id)
        raise


async def decrease_cart_item_quantity(
    session: AsyncSession,
    cart_item_id: int,
) -> Optional[CartItem]:
    try:
        result = await session.execute(select(CartItem).where(CartItem.id == cart_item_id))
        cart_item = result.scalar_one_or_none()
        if cart_item is None:
            return None

        if cart_item.quantity <= 1:
            await session.delete(cart_item)
            await session.commit()
            return None

        cart_item.quantity -= 1
        await session.commit()
        await session.refresh(cart_item)
        return cart_item
    except SQLAlchemyError:
        await session.rollback()
        logger.exception("Failed to decrease cart_item_id=%s", cart_item_id)
        raise


async def remove_cart_item(
    session: AsyncSession,
    cart_item_id: int,
) -> bool:
    try:
        result = await session.execute(select(CartItem).where(CartItem.id == cart_item_id))
        cart_item = result.scalar_one_or_none()
        if cart_item is None:
            return False

        await session.delete(cart_item)
        await session.commit()
        return True
    except SQLAlchemyError:
        await session.rollback()
        logger.exception("Failed to remove cart_item_id=%s", cart_item_id)
        raise
