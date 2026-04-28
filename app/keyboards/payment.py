from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.callbacks.payment import RETRY_PAYMENT_ACTION, PaymentCallback
from app.ui_text import get_ui_text


def build_payment_confirmation_keyboard(confirmation_url: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=get_ui_text("payment", "pay_button"),
                    url=confirmation_url,
                )
            ]
        ]
    )


def build_retry_payment_keyboard(order_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=get_ui_text("payment", "retry_button"),
                    callback_data=PaymentCallback(
                        action=RETRY_PAYMENT_ACTION,
                        order_id=order_id,
                    ).pack(),
                )
            ]
        ]
    )
