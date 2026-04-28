import logging
import re
from dataclasses import dataclass
from decimal import Decimal

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
CANONICAL_ORDER_STATUSES = (
    "new",
    "paid",
    "assembling",
    "delivering",
    "completed",
    "cancelled",
)
TERMINAL_ORDER_STATUSES = ("completed", "cancelled")
OPERATOR_ALLOWED_STATUS_TRANSITIONS = {
    "new": ("new", "cancelled"),
    "paid": ("paid", "assembling", "cancelled"),
    "assembling": ("assembling", "delivering", "cancelled"),
    "delivering": ("delivering", "completed", "cancelled"),
    "completed": ("completed",),
    "cancelled": ("cancelled",),
}


class OrderCreationError(Exception):
    pass


class EmptyCartError(OrderCreationError):
    pass


class InvalidPhoneError(OrderCreationError):
    pass


class InvalidAddressError(OrderCreationError):
    pass


class InvalidOrderStatusError(ValueError):
    pass


class InvalidOrderStatusTransitionError(ValueError):
    pass


@dataclass(slots=True)
class CheckoutSummary:
    phone: str
    shipping_address: str
    total_amount: Decimal


@dataclass(slots=True)
class OrderStatusUpdateResult:
    order: Order
    previous_status: str
    changed: bool


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


def get_operator_available_statuses(current_status: str) -> tuple[str, ...]:
    return OPERATOR_ALLOWED_STATUS_TRANSITIONS.get(current_status, (current_status,))


async def get_active_orders_for_operator(session: AsyncSession) -> list[Order]:
    result = await session.execute(
        select(Order)
        .options(selectinload(Order.user), selectinload(Order.payment_attempts))
        .where(Order.status.not_in(TERMINAL_ORDER_STATUSES))
        .order_by(Order.created_at.desc(), Order.id.desc())
    )
    return list(result.scalars().all())


async def get_order_by_id(session: AsyncSession, order_id: int) -> Order | None:
    result = await session.execute(
        select(Order)
        .options(selectinload(Order.user), selectinload(Order.payment_attempts))
        .where(Order.id == order_id)
    )
    return result.scalar_one_or_none()


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


async def update_order_status(
    session: AsyncSession,
    order_id: int,
    status: str,
) -> Order | None:
    result = await update_order_status_with_meta(session, order_id, status)
    if result is None:
        return None
    return result.order


async def update_order_status_with_meta(
    session: AsyncSession,
    order_id: int,
    status: str,
) -> OrderStatusUpdateResult | None:
    if status not in CANONICAL_ORDER_STATUSES:
        raise InvalidOrderStatusError(status)

    try:
        order = await get_order_by_id(session, order_id)
        if order is None:
            return None

        previous_status = order.status
        changed = previous_status != status
        if changed:
            order.status = status
            await session.commit()
            refreshed_order = await get_order_by_id(session, order_id)
            if refreshed_order is not None:
                order = refreshed_order

        return OrderStatusUpdateResult(
            order=order,
            previous_status=previous_status,
            changed=changed,
        )
    except SQLAlchemyError:
        await session.rollback()
        logger.exception("Failed to update order status order_id=%s status=%s", order_id, status)
        raise


async def update_order_status_from_operator(
    session: AsyncSession,
    order_id: int,
    status: str,
) -> OrderStatusUpdateResult | None:
    order = await get_order_by_id(session, order_id)
    if order is None:
        return None

    if status not in get_operator_available_statuses(order.status):
        raise InvalidOrderStatusTransitionError(
            f"transition {order.status} -> {status} is not allowed"
        )

    return await update_order_status_with_meta(session, order_id, status)


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
