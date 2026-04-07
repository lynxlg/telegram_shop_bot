from decimal import Decimal

from app.models.cart import Cart
from app.models.cart_item import CartItem


EMPTY_CART_TEXT = "Корзина пуста."


def _format_money(value: Decimal) -> str:
    return f"{value:.2f} ₽"


def format_cart_item_total(cart_item: CartItem) -> str:
    item_total = cart_item.product.price * cart_item.quantity
    return _format_money(item_total)


def format_cart_total(cart: Cart) -> str:
    total = sum(
        (cart_item.product.price * cart_item.quantity for cart_item in cart.items),
        start=Decimal("0.00"),
    )
    return _format_money(total)


def format_cart_text(cart: Cart | None) -> str:
    if cart is None or not cart.items:
        return EMPTY_CART_TEXT

    lines = ["Корзина:", ""]
    for index, cart_item in enumerate(cart.items, start=1):
        lines.append(
            (
                f"{index}. {cart_item.product.name}\n"
                f"Цена: {_format_money(cart_item.product.price)}\n"
                f"Количество: {cart_item.quantity}\n"
                f"Сумма: {format_cart_item_total(cart_item)}"
            )
        )
        lines.append("")

    lines.append(f"Итого: {format_cart_total(cart)}")
    return "\n".join(lines)
