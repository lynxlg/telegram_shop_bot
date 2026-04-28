from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.callbacks.operator_orders import (
    BACK_TO_LIST_ACTION,
    OPEN_ORDER_ACTION,
    UPDATE_STATUS_ACTION,
    OperatorOrdersCallback,
)
from app.models.order import Order
from app.services.order import get_operator_available_statuses
from app.services.order_text import get_order_status_label
from app.ui_text import get_ui_text

BACK_TO_ORDERS_BUTTON_TEXT = get_ui_text("operator_orders", "back_to_list_button")


def build_operator_orders_keyboard(orders: list[Order]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for order in orders:
        builder.button(
            text=order.order_number,
            callback_data=OperatorOrdersCallback(
                action=OPEN_ORDER_ACTION,
                order_id=order.id,
            ),
        )
    builder.adjust(1)
    return builder.as_markup()


def build_operator_order_detail_keyboard(
    order_id: int, current_status: str
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for status in get_operator_available_statuses(current_status):
        label = get_order_status_label(status)
        if status == current_status:
            label = f"• {label}"
        builder.button(
            text=label,
            callback_data=OperatorOrdersCallback(
                action=UPDATE_STATUS_ACTION,
                order_id=order_id,
                status=status,
            ),
        )

    builder.button(
        text=BACK_TO_ORDERS_BUTTON_TEXT,
        callback_data=OperatorOrdersCallback(
            action=BACK_TO_LIST_ACTION,
        ),
    )
    builder.adjust(2, 2, 1)
    return builder.as_markup()
