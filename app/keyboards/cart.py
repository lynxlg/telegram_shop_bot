from typing import List

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)

from app.callbacks.cart import (
    CANCEL_CHECKOUT_ACTION,
    CONFIRM_ORDER_ACTION,
    CartCallback,
    DECREASE_ACTION,
    INCREASE_ACTION,
    REMOVE_ACTION,
    START_CHECKOUT_ACTION,
)
from app.models.cart_item import CartItem
from app.ui_text import format_ui_text, get_ui_text


CHECKOUT_CANCEL_TEXT = get_ui_text("checkout", "cancel_checkout_button")


def build_cart_keyboard(cart_items: List[CartItem]) -> InlineKeyboardMarkup:
    inline_keyboard = []

    for cart_item in cart_items:
        inline_keyboard.append(
            [
                InlineKeyboardButton(
                    text=get_ui_text("cart", "increase_button"),
                    callback_data=CartCallback(
                        action=INCREASE_ACTION,
                        cart_item_id=cart_item.id,
                    ).pack(),
                ),
                InlineKeyboardButton(
                    text=get_ui_text("cart", "decrease_button"),
                    callback_data=CartCallback(
                        action=DECREASE_ACTION,
                        cart_item_id=cart_item.id,
                    ).pack(),
                ),
                InlineKeyboardButton(
                    text=format_ui_text(
                        "cart",
                        "remove_item_button",
                        product_name=cart_item.product.name,
                    ),
                    callback_data=CartCallback(
                        action=REMOVE_ACTION,
                        cart_item_id=cart_item.id,
                    ).pack(),
                ),
            ]
        )

    inline_keyboard.append(
        [
            InlineKeyboardButton(
                text=get_ui_text("cart", "checkout_button"),
                callback_data=CartCallback(action=START_CHECKOUT_ACTION).pack(),
            )
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=inline_keyboard)


def build_checkout_confirmation_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=get_ui_text("checkout", "confirm_button"),
                    callback_data=CartCallback(action=CONFIRM_ORDER_ACTION).pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text=get_ui_text("checkout", "cancel_button"),
                    callback_data=CartCallback(action=CANCEL_CHECKOUT_ACTION).pack(),
                )
            ],
        ]
    )


def build_checkout_phone_keyboard(saved_phone: str | None = None) -> ReplyKeyboardMarkup:
    rows = [
        [
            KeyboardButton(
                text=get_ui_text("checkout", "send_phone_button"),
                request_contact=True,
            )
        ],
    ]
    if saved_phone:
        rows.append([KeyboardButton(text=saved_phone)])
    rows.append([KeyboardButton(text=CHECKOUT_CANCEL_TEXT)])

    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)


def build_checkout_address_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=CHECKOUT_CANCEL_TEXT)]],
        resize_keyboard=True,
    )
