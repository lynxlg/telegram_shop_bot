from aiogram.filters.callback_data import CallbackData


class PaymentCallback(CallbackData, prefix="payment"):
    action: str
    order_id: int


RETRY_PAYMENT_ACTION = "retry"
