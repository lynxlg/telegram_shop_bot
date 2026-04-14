from aiogram.filters.callback_data import CallbackData


class CartCallback(CallbackData, prefix="cart"):
    action: str
    cart_item_id: int | None = None


INCREASE_ACTION = "increase"
DECREASE_ACTION = "decrease"
REMOVE_ACTION = "remove"
START_CHECKOUT_ACTION = "checkout"
CONFIRM_ORDER_ACTION = "confirm_order"
CANCEL_CHECKOUT_ACTION = "cancel_checkout"
