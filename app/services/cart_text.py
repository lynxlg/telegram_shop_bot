from decimal import Decimal

from app.models.cart import Cart
from app.models.cart_item import CartItem
from app.services.order import CheckoutSummary
from app.ui_text import format_ui_text, get_ui_text

EMPTY_CART_TEXT = get_ui_text("cart", "empty")
CHECKOUT_SUCCESS_TEXT = get_ui_text("checkout", "success")


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

    lines = [get_ui_text("cart", "title"), ""]
    for index, cart_item in enumerate(cart.items, start=1):
        lines.append(
            format_ui_text(
                "cart",
                "item_line",
                index=index,
                name=cart_item.product.name,
                price=_format_money(cart_item.product.price),
                quantity=cart_item.quantity,
                total=format_cart_item_total(cart_item),
            )
        )
        lines.append("")

    lines.append(format_ui_text("cart", "total_label", total=format_cart_total(cart)))
    return "\n".join(lines)


def format_checkout_confirmation_text(cart: Cart, summary: CheckoutSummary) -> str:
    return (
        f"{format_cart_text(cart)}\n\n"
        f"{get_ui_text('checkout', 'confirmation_title')}\n"
        f"{format_ui_text('checkout', 'phone_label', phone=summary.phone)}\n"
        f"{format_ui_text('checkout', 'address_label', address=summary.shipping_address)}\n"
        f"{format_ui_text('checkout', 'confirmation_total_label', total=_format_money(summary.total_amount))}"
    )


def format_order_created_text(order_number: str) -> str:
    return (
        f"{CHECKOUT_SUCCESS_TEXT}\n"
        f"{format_ui_text('checkout', 'order_number_label', order_number=order_number)}"
    )
