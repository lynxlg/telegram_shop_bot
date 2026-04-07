from typing import List

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.callbacks.cart import (
    CartCallback,
    DECREASE_ACTION,
    INCREASE_ACTION,
    REMOVE_ACTION,
)
from app.models.cart_item import CartItem


def build_cart_keyboard(cart_items: List[CartItem]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    for cart_item in cart_items:
        builder.button(
            text="+",
            callback_data=CartCallback(
                action=INCREASE_ACTION,
                cart_item_id=cart_item.id,
            ),
        )
        builder.button(
            text="-",
            callback_data=CartCallback(
                action=DECREASE_ACTION,
                cart_item_id=cart_item.id,
            ),
        )
        builder.button(
            text=f"Удалить {cart_item.product.name}",
            callback_data=CartCallback(
                action=REMOVE_ACTION,
                cart_item_id=cart_item.id,
            ),
        )
        builder.adjust(3)

    return builder.as_markup()
