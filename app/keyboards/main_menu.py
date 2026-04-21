from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

from app.ui_text import get_ui_text

CATALOG_BUTTON_TEXT = get_ui_text("main_menu", "catalog_button")
CART_BUTTON_TEXT = get_ui_text("main_menu", "cart_button")
ORDER_STATUS_BUTTON_TEXT = get_ui_text("main_menu", "order_status_button")
OPERATOR_ORDERS_BUTTON_TEXT = get_ui_text("main_menu", "operator_orders_button")
ADMIN_CATALOG_BUTTON_TEXT = get_ui_text("main_menu", "admin_catalog_button")
OPERATOR_ROLES = {"operator", "admin"}
ADMIN_ROLES = {"admin"}


def get_main_menu_keyboard(role: str = "user") -> ReplyKeyboardMarkup:
    rows = [
        [
            KeyboardButton(text=CATALOG_BUTTON_TEXT),
            KeyboardButton(text=CART_BUTTON_TEXT),
        ],
        [KeyboardButton(text=ORDER_STATUS_BUTTON_TEXT)],
    ]
    if role in OPERATOR_ROLES:
        rows.append([KeyboardButton(text=OPERATOR_ORDERS_BUTTON_TEXT)])
    if role in ADMIN_ROLES:
        rows.append([KeyboardButton(text=ADMIN_CATALOG_BUTTON_TEXT)])

    return ReplyKeyboardMarkup(
        keyboard=rows,
        resize_keyboard=True,
    )
