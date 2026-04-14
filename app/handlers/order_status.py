import logging

from aiogram import F, Router
from aiogram.types import Message
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.order import get_active_orders_by_telegram_id
from app.services.order_text import (
    EMPTY_ACTIVE_ORDERS_TEXT,
    ORDER_STATUS_LOAD_ERROR_TEXT,
    format_active_orders_text,
)
from app.ui_text import get_ui_text


logger = logging.getLogger(__name__)
router = Router()

ORDER_STATUS_BUTTON_TEXT = get_ui_text("main_menu", "order_status_button")


@router.message(F.text == ORDER_STATUS_BUTTON_TEXT)
async def show_active_order_statuses(message: Message, db: AsyncSession) -> None:
    telegram_user = message.from_user
    if telegram_user is None:
        await message.answer(ORDER_STATUS_LOAD_ERROR_TEXT)
        return

    try:
        orders = await get_active_orders_by_telegram_id(db, telegram_user.id)
    except SQLAlchemyError:
        logger.exception(
            "Database error while loading active orders telegram_id=%s",
            telegram_user.id,
        )
        await message.answer(ORDER_STATUS_LOAD_ERROR_TEXT)
        return

    if not orders:
        await message.answer(EMPTY_ACTIVE_ORDERS_TEXT)
        return

    await message.answer(format_active_orders_text(orders))
