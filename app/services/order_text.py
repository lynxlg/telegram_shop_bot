from app.models.order import Order
from app.ui_text import format_ui_text, get_ui_text


EMPTY_ACTIVE_ORDERS_TEXT = get_ui_text("order_status", "empty")
ORDER_STATUS_LOAD_ERROR_TEXT = get_ui_text("order_status", "load_error")

_STATUS_LABELS = {
    "new": get_ui_text("order_status", "status_new"),
    "accepted": get_ui_text("order_status", "status_accepted"),
    "assembling": get_ui_text("order_status", "status_assembling"),
    "delivering": get_ui_text("order_status", "status_delivering"),
    "completed": get_ui_text("order_status", "status_completed"),
    "cancelled": get_ui_text("order_status", "status_cancelled"),
}


def format_order_status(status: str) -> str:
    return _STATUS_LABELS.get(
        status,
        format_ui_text("order_status", "status_unknown", status=status),
    )


def format_active_orders_text(orders: list[Order]) -> str:
    lines = [get_ui_text("order_status", "title"), ""]
    for index, order in enumerate(orders, start=1):
        lines.append(
            format_ui_text(
                "order_status",
                "item_line",
                index=index,
                order_number=order.order_number,
                status=format_order_status(order.status),
            )
        )

    return "\n".join(lines)
