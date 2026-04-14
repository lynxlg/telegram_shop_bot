from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

from app.ui_text import get_ui_text


CATALOG_BUTTON_TEXT = get_ui_text("main_menu", "catalog_button")
CART_BUTTON_TEXT = get_ui_text("main_menu", "cart_button")
ORDER_STATUS_BUTTON_TEXT = get_ui_text("main_menu", "order_status_button")


def get_main_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text=CATALOG_BUTTON_TEXT),
                KeyboardButton(text=CART_BUTTON_TEXT),
            ],
            [KeyboardButton(text=ORDER_STATUS_BUTTON_TEXT)],
        ],
        resize_keyboard=True,
    )
