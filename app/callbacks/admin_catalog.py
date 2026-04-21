from typing import Optional

from aiogram.filters.callback_data import CallbackData


class AdminCatalogCallback(CallbackData, prefix="admin_catalog"):
    action: str
    category_id: Optional[int] = None
    product_id: Optional[int] = None
    field: Optional[str] = None


OPEN_CATEGORY_ACTION = "open_category"
OPEN_PRODUCT_ACTION = "open_product"
START_CREATE_CATEGORY_ACTION = "create_category"
START_EDIT_CATEGORY_ACTION = "edit_category"
DELETE_CATEGORY_ACTION = "delete_category"
START_CREATE_PRODUCT_ACTION = "create_product"
START_EDIT_PRODUCT_ACTION = "edit_product"
TOGGLE_PRODUCT_ACTIVE_ACTION = "toggle_product"
DELETE_PRODUCT_ACTION = "delete_product"
BACK_TO_ROOT_ACTION = "back_to_root"
BACK_TO_CATEGORY_ACTION = "back_to_category"
