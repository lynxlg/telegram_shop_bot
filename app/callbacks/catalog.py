from typing import Optional

from aiogram.filters.callback_data import CallbackData


class CatalogCallback(CallbackData, prefix="catalog"):
    action: str
    category_id: Optional[int] = None
    product_id: Optional[int] = None
    parent_category_id: Optional[int] = None
    page: Optional[int] = None


OPEN_CATEGORY_ACTION = "open_category"
OPEN_PRODUCT_ACTION = "open_product"
GO_BACK_ACTION = "go_back"
ADD_TO_CART_ACTION = "add_to_cart"
