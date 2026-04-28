import logging

from aiogram import F, Router
from aiogram.types import CallbackQuery
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.callbacks.payment import RETRY_PAYMENT_ACTION, PaymentCallback
from app.keyboards.payment import build_payment_confirmation_keyboard
from app.services.payment import (
    PaymentAlreadyCompletedError,
    PaymentAttemptNotFoundError,
    PaymentConfigurationError,
    PaymentOrderAccessError,
    PaymentProviderError,
    retry_payment_for_order,
)
from app.ui_text import format_ui_text

logger = logging.getLogger(__name__)
router = Router()


@router.callback_query(PaymentCallback.filter(F.action == RETRY_PAYMENT_ACTION))
async def retry_payment(
    callback: CallbackQuery,
    callback_data: PaymentCallback,
    db: AsyncSession,
) -> None:
    try:
        attempt = await retry_payment_for_order(
            db,
            order_id=callback_data.order_id,
            telegram_id=callback.from_user.id,
        )
        if not attempt.confirmation_url:
            await callback.answer(
                format_ui_text("payment", "payment_create_error"), show_alert=True
            )
            return
        if callback.message is not None:
            await callback.message.edit_text(
                format_ui_text(
                    "payment",
                    "retry_ready",
                    order_id=callback_data.order_id,
                ),
                reply_markup=build_payment_confirmation_keyboard(attempt.confirmation_url or ""),
            )
        await callback.answer()
    except PaymentAlreadyCompletedError:
        await callback.answer(format_ui_text("payment", "already_paid"), show_alert=True)
    except (PaymentAttemptNotFoundError, PaymentOrderAccessError):
        await callback.answer(format_ui_text("payment", "order_not_found"), show_alert=True)
    except PaymentConfigurationError:
        await callback.answer(format_ui_text("payment", "payment_unavailable"), show_alert=True)
    except PaymentProviderError:
        await callback.answer(format_ui_text("payment", "payment_create_error"), show_alert=True)
    except SQLAlchemyError:
        logger.exception(
            "Database error while retrying payment telegram_id=%s order_id=%s",
            callback.from_user.id,
            callback_data.order_id,
        )
        await callback.answer(format_ui_text("payment", "payment_create_error"), show_alert=True)
