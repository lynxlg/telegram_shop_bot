from decimal import Decimal

from app.models.order import Order
from app.models.payment_attempt import PaymentAttempt
from app.ui_text import format_ui_text, get_ui_text

EMPTY_ACTIVE_ORDERS_TEXT = get_ui_text("order_status", "empty")
ORDER_STATUS_LOAD_ERROR_TEXT = get_ui_text("order_status", "load_error")
OPERATOR_ORDERS_EMPTY_TEXT = get_ui_text("operator_orders", "empty")
OPERATOR_ORDERS_LOAD_ERROR_TEXT = get_ui_text("operator_orders", "load_error")
OPERATOR_ORDERS_ACCESS_DENIED_TEXT = get_ui_text("operator_orders", "access_denied")
OPERATOR_ORDERS_INVALID_TRANSITION_TEXT = get_ui_text("operator_orders", "invalid_transition")

_STATUS_LABELS = {
    "new": get_ui_text("order_status", "status_new"),
    "accepted": get_ui_text("order_status", "status_accepted"),
    "paid": get_ui_text("order_status", "status_paid"),
    "assembling": get_ui_text("order_status", "status_assembling"),
    "delivering": get_ui_text("order_status", "status_delivering"),
    "completed": get_ui_text("order_status", "status_completed"),
    "cancelled": get_ui_text("order_status", "status_cancelled"),
}


def get_order_status_label(status: str) -> str:
    return _STATUS_LABELS.get(
        status,
        format_ui_text("order_status", "status_unknown", status=status),
    )


def format_order_status(status: str) -> str:
    return get_order_status_label(status)


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


def format_operator_orders_list_text(orders: list[Order]) -> str:
    if not orders:
        return OPERATOR_ORDERS_EMPTY_TEXT

    lines = [get_ui_text("operator_orders", "title"), ""]
    for index, order in enumerate(orders, start=1):
        customer_name = order.user.first_name if order.user is not None else "Покупатель"
        lines.append(
            format_ui_text(
                "operator_orders",
                "item_line",
                index=index,
                order_number=order.order_number,
                customer_name=customer_name,
                status=get_order_status_label(order.status),
            )
        )

    return "\n".join(lines)


def format_operator_order_details_text(order: Order) -> str:
    customer_name = order.user.first_name if order.user is not None else "Покупатель"
    total_amount = Decimal(str(order.total_amount))
    latest_attempt = order.payment_attempts[0] if order.payment_attempts else None
    payment_facts = format_payment_attempt_details_text(latest_attempt, len(order.payment_attempts))
    return format_ui_text(
        "operator_orders",
        "details",
        order_number=order.order_number,
        customer_name=customer_name,
        status=get_order_status_label(order.status),
        phone=order.phone,
        shipping_address=order.shipping_address,
        total_amount=f"{total_amount:.2f} ₽",
        payment_facts=payment_facts,
    )


def format_order_status_notification_text(order: Order) -> str:
    return format_ui_text(
        "order_notifications",
        "status_changed",
        order_number=order.order_number,
        status=get_order_status_label(order.status),
    )


def get_payment_attempt_status_label(status: str) -> str:
    try:
        return get_ui_text("payment", f"status_{status}")
    except KeyError:
        return status


def format_payment_attempt_details_text(
    attempt: PaymentAttempt | None,
    attempts_count: int,
) -> str:
    if attempt is None:
        return format_ui_text("operator_orders", "payment_missing", attempts_count=attempts_count)

    failure_reason = attempt.failure_reason or get_ui_text(
        "operator_orders", "payment_failure_empty"
    )
    payment_method = attempt.payment_method_type or get_ui_text(
        "operator_orders", "payment_method_empty"
    )
    provider_payment_id = attempt.provider_payment_id or get_ui_text(
        "operator_orders", "payment_id_empty"
    )
    return format_ui_text(
        "operator_orders",
        "payment_details",
        attempts_count=attempts_count,
        payment_status=get_payment_attempt_status_label(attempt.status),
        provider_payment_id=provider_payment_id,
        payment_method=payment_method,
        failure_reason=failure_reason,
    )
