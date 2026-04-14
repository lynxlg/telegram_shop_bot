import logging
from dataclasses import dataclass
from decimal import Decimal
import re

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.cart import Cart
from app.models.cart_item import CartItem
from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.user import User


logger = logging.getLogger(__name__)

MIN_PHONE_DIGITS = 10
MIN_ADDRESS_LENGTH = 5
ORDER_NUMBER_PREFIX = "ORD-"
TERMINAL_ORDER_STATUSES = ("completed", "cancelled")


class OrderCreationError(Exception):
    pass


class EmptyCartError(OrderCreationError):
    pass


class InvalidPhoneError(OrderCreationError):
    pass


class InvalidAddressError(OrderCreationError):
    pass


@dataclass(slots=True)
class CheckoutSummary:
    phone: str
    shipping_address: str
    total_amount: Decimal


def normalize_phone(phone: str) -> str:
    normalized = re.sub(r"[^\d+]", "", phone.strip())
    if normalized.startswith("8") and len(re.sub(r"\D", "", normalized)) == 11:
        normalized = "+7" + normalized[1:]
    elif not normalized.startswith("+") and normalized:
        normalized = "+" + normalized

    digits_only = re.sub(r"\D", "", normalized)
    if len(digits_only) < MIN_PHONE_DIGITS:
        raise InvalidPhoneError("phone is too short")

    return normalized


def normalize_address(address: str) -> str:
    normalized = " ".join(address.split())
    if len(normalized) < MIN_ADDRESS_LENGTH:
        raise InvalidAddressError("address is too short")
    return normalized


def build_checkout_summary(cart: Cart, phone: str, shipping_address: str) -> CheckoutSummary:
    total_amount = sum(
        (cart_item.product.price * cart_item.quantity for cart_item in cart.items),
        start=Decimal("0.00"),
    )
    return CheckoutSummary(
        phone=normalize_phone(phone),
        shipping_address=normalize_address(shipping_address),
        total_amount=total_amount,
    )


def _build_order_number(order_id: int) -> str:
    return f"{ORDER_NUMBER_PREFIX}{order_id:06d}"


async def get_active_orders_by_telegram_id(
    session: AsyncSession,
    telegram_id: int,
) -> list[Order]:
    result = await session.execute(
        select(Order)
        .join(User, User.id == Order.user_id)
        .where(User.telegram_id == telegram_id)
        .where(Order.status.not_in(TERMINAL_ORDER_STATUSES))
        .order_by(Order.created_at.desc(), Order.id.desc())
    )
    return list(result.scalars().all())


async def create_order_from_cart(
    session: AsyncSession,
    telegram_id: int,
    phone: str,
    shipping_address: str,
) -> Order:
    try:
        result = await session.execute(select(User).where(User.telegram_id == telegram_id))
        user = result.scalar_one_or_none()
        if user is None:
            raise EmptyCartError("user not found for checkout")

        cart_result = await session.execute(
            select(Cart)
            .options(selectinload(Cart.items).selectinload(CartItem.product))
            .where(Cart.user_id == user.id)
        )
        cart = cart_result.scalar_one_or_none()
        if cart is None or not cart.items:
            raise EmptyCartError("cart is empty")

        summary = build_checkout_summary(cart, phone, shipping_address)

        order = Order(
            user_id=user.id,
            order_number="pending",
            status="new",
            phone=summary.phone,
            shipping_address=summary.shipping_address,
            total_amount=summary.total_amount,
        )
        session.add(order)
        await session.flush()

        order.order_number = _build_order_number(order.id)

        for cart_item in cart.items:
            line_total = cart_item.product.price * cart_item.quantity
            session.add(
                OrderItem(
                    order_id=order.id,
                    product_id=cart_item.product_id,
                    product_name=cart_item.product.name,
                    unit_price=cart_item.product.price,
                    quantity=cart_item.quantity,
                    line_total=line_total,
                )
            )

        user.phone = summary.phone

        for cart_item in list(cart.items):
            await session.delete(cart_item)
        await session.flush()
        cart.items.clear()

        await session.commit()
        await session.refresh(order)
        return order
    except OrderCreationError:
        await session.rollback()
        raise
    except SQLAlchemyError:
        await session.rollback()
        logger.exception("Failed to create order for telegram_id=%s", telegram_id)
        raise
