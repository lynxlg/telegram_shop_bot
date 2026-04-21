from aiogram.filters.callback_data import CallbackData


class OperatorOrdersCallback(CallbackData, prefix="operator_orders"):
    action: str
    order_id: int | None = None
    status: str | None = None


OPEN_ORDER_ACTION = "open_order"
BACK_TO_LIST_ACTION = "back_to_list"
UPDATE_STATUS_ACTION = "update_status"
