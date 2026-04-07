from aiogram.filters.callback_data import CallbackData


class CartCallback(CallbackData, prefix="cart"):
    action: str
    cart_item_id: int


INCREASE_ACTION = "increase"
DECREASE_ACTION = "decrease"
REMOVE_ACTION = "remove"
