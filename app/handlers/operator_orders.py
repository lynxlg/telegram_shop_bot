import logging

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.callbacks.operator_orders import (
    BACK_TO_LIST_ACTION,
    OPEN_ORDER_ACTION,
    UPDATE_STATUS_ACTION,
    OperatorOrdersCallback,
)
from app.keyboards.operator_orders import (
    build_operator_order_detail_keyboard,
    build_operator_orders_keyboard,
)
from app.models.user import User
from app.services.order import (
    get_active_orders_for_operator,
    get_order_by_id,
    update_order_status,
)
from app.services.order_text import (
    OPERATOR_ORDERS_ACCESS_DENIED_TEXT,
    OPERATOR_ORDERS_EMPTY_TEXT,
    OPERATOR_ORDERS_LOAD_ERROR_TEXT,
    format_operator_order_details_text,
    format_operator_orders_list_text,
)
from app.ui_text import get_ui_text

logger = logging.getLogger(__name__)
router = Router()

OPERATOR_ORDERS_BUTTON_TEXT = get_ui_text("main_menu", "operator_orders_button")
ALLOWED_ROLES = {"operator", "admin"}


async def _get_user_role(db: AsyncSession, telegram_id: int) -> str | None:
    result = await db.execute(select(User.role).where(User.telegram_id == telegram_id))
    return result.scalar_one_or_none()


async def _is_operator(db: AsyncSession, telegram_id: int) -> bool:
    role = await _get_user_role(db, telegram_id)
    return role in ALLOWED_ROLES


async def _render_orders_list(target: Message | CallbackQuery, db: AsyncSession) -> None:
    orders = await get_active_orders_for_operator(db)
    text = format_operator_orders_list_text(orders)
    markup = build_operator_orders_keyboard(orders) if orders else None

    if not hasattr(target, "message"):
        await target.answer(text, reply_markup=markup)
        return

    if target.message is None:
        await target.answer()
        return

    await target.message.edit_text(text, reply_markup=markup)
    await target.answer()


async def _render_order_details(callback: CallbackQuery, db: AsyncSession, order_id: int) -> None:
    order = await get_order_by_id(db, order_id)
    if callback.message is None:
        await callback.answer()
        return

    if order is None:
        await callback.message.edit_text(OPERATOR_ORDERS_EMPTY_TEXT)
        await callback.answer()
        return

    await callback.message.edit_text(
        format_operator_order_details_text(order),
        reply_markup=build_operator_order_detail_keyboard(order.id, order.status),
    )
    await callback.answer()


@router.message(F.text == OPERATOR_ORDERS_BUTTON_TEXT)
async def show_operator_orders(message: Message, db: AsyncSession) -> None:
    telegram_user = message.from_user
    if telegram_user is None:
        await message.answer(OPERATOR_ORDERS_LOAD_ERROR_TEXT)
        return

    try:
        if not await _is_operator(db, telegram_user.id):
            await message.answer(OPERATOR_ORDERS_ACCESS_DENIED_TEXT)
            return

        await _render_orders_list(message, db)
    except SQLAlchemyError:
        logger.exception(
            "Database error while loading operator orders telegram_id=%s", telegram_user.id
        )
        await message.answer(OPERATOR_ORDERS_LOAD_ERROR_TEXT)


@router.callback_query(OperatorOrdersCallback.filter(F.action == OPEN_ORDER_ACTION))
async def open_operator_order(
    callback: CallbackQuery,
    callback_data: OperatorOrdersCallback,
    db: AsyncSession,
) -> None:
    try:
        if not await _is_operator(db, callback.from_user.id):
            await callback.answer(OPERATOR_ORDERS_ACCESS_DENIED_TEXT, show_alert=True)
            return

        if callback_data.order_id is None:
            await callback.answer()
            return

        await _render_order_details(callback, db, callback_data.order_id)
    except SQLAlchemyError:
        logger.exception(
            "Database error while opening operator order telegram_id=%s order_id=%s",
            callback.from_user.id,
            callback_data.order_id,
        )
        if callback.message is not None:
            await callback.message.edit_text(OPERATOR_ORDERS_LOAD_ERROR_TEXT)
        await callback.answer()


@router.callback_query(OperatorOrdersCallback.filter(F.action == BACK_TO_LIST_ACTION))
async def back_to_operator_orders(callback: CallbackQuery, db: AsyncSession) -> None:
    try:
        if not await _is_operator(db, callback.from_user.id):
            await callback.answer(OPERATOR_ORDERS_ACCESS_DENIED_TEXT, show_alert=True)
            return

        await _render_orders_list(callback, db)
    except SQLAlchemyError:
        logger.exception(
            "Database error while returning to operator orders telegram_id=%s",
            callback.from_user.id,
        )
        if callback.message is not None:
            await callback.message.edit_text(OPERATOR_ORDERS_LOAD_ERROR_TEXT)
        await callback.answer()


@router.callback_query(OperatorOrdersCallback.filter(F.action == UPDATE_STATUS_ACTION))
async def change_operator_order_status(
    callback: CallbackQuery,
    callback_data: OperatorOrdersCallback,
    db: AsyncSession,
) -> None:
    try:
        if not await _is_operator(db, callback.from_user.id):
            await callback.answer(OPERATOR_ORDERS_ACCESS_DENIED_TEXT, show_alert=True)
            return

        if callback_data.order_id is None or callback_data.status is None:
            await callback.answer()
            return

        order = await update_order_status(db, callback_data.order_id, callback_data.status)
        if callback.message is None:
            await callback.answer()
            return

        if order is None:
            await callback.message.edit_text(OPERATOR_ORDERS_EMPTY_TEXT)
            await callback.answer()
            return

        await callback.message.edit_text(
            format_operator_order_details_text(order),
            reply_markup=build_operator_order_detail_keyboard(order.id, order.status),
        )
        await callback.answer()
    except SQLAlchemyError:
        logger.exception(
            "Database error while updating operator order telegram_id=%s order_id=%s status=%s",
            callback.from_user.id,
            callback_data.order_id,
            callback_data.status,
        )
        if callback.message is not None:
            await callback.message.edit_text(OPERATOR_ORDERS_LOAD_ERROR_TEXT)
        await callback.answer()
