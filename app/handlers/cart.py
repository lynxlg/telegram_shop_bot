import logging

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.callbacks.cart import (
    CartCallback,
    DECREASE_ACTION,
    INCREASE_ACTION,
    REMOVE_ACTION,
)
from app.keyboards.cart import build_cart_keyboard
from app.services.cart import (
    decrease_cart_item_quantity,
    get_cart_by_telegram_id,
    increase_cart_item_quantity,
    remove_cart_item,
)
from app.services.cart_text import EMPTY_CART_TEXT, format_cart_text


logger = logging.getLogger(__name__)
router = Router()

ITEM_NOT_FOUND_TEXT = "Позиция корзины не найдена."
CART_UPDATE_ERROR_TEXT = "Не удалось обновить корзину. Попробуйте позже."


async def _render_cart(message: Message, db: AsyncSession, telegram_id: int) -> None:
    cart = await get_cart_by_telegram_id(db, telegram_id)
    text = format_cart_text(cart)
    if cart is None or not cart.items:
        await message.answer(text)
        return

    await message.answer(text, reply_markup=build_cart_keyboard(cart.items))


async def _update_cart_view(
    callback: CallbackQuery,
    db: AsyncSession,
    telegram_id: int,
) -> None:
    if callback.message is None:
        await callback.answer()
        return

    cart = await get_cart_by_telegram_id(db, telegram_id)
    text = format_cart_text(cart)
    if cart is None or not cart.items:
        await callback.message.edit_text(text)
        await callback.answer()
        return

    await callback.message.edit_text(
        text,
        reply_markup=build_cart_keyboard(cart.items),
    )
    await callback.answer()


@router.message(F.text == "Корзина")
async def open_cart(message: Message, db: AsyncSession) -> None:
    telegram_user = message.from_user
    if telegram_user is None:
        await message.answer(EMPTY_CART_TEXT)
        return

    try:
        await _render_cart(message, db, telegram_user.id)
    except SQLAlchemyError:
        logger.exception("Database error while opening cart telegram_id=%s", telegram_user.id)
        await message.answer(CART_UPDATE_ERROR_TEXT)


@router.callback_query(CartCallback.filter(F.action == INCREASE_ACTION))
async def increase_item(
    callback: CallbackQuery,
    callback_data: CartCallback,
    db: AsyncSession,
) -> None:
    try:
        cart_item = await increase_cart_item_quantity(db, callback_data.cart_item_id)
        if cart_item is None:
            if callback.message is not None:
                await callback.message.edit_text(ITEM_NOT_FOUND_TEXT)
            await callback.answer()
            return

        await _update_cart_view(callback, db, callback.from_user.id)
    except SQLAlchemyError:
        logger.exception("Database error while increasing cart_item_id=%s", callback_data.cart_item_id)
        if callback.message is not None:
            await callback.message.edit_text(CART_UPDATE_ERROR_TEXT)
        await callback.answer()


@router.callback_query(CartCallback.filter(F.action == DECREASE_ACTION))
async def decrease_item(
    callback: CallbackQuery,
    callback_data: CartCallback,
    db: AsyncSession,
) -> None:
    try:
        result = await decrease_cart_item_quantity(db, callback_data.cart_item_id)
        cart = await get_cart_by_telegram_id(db, callback.from_user.id)
        if result is None and cart is not None and all(
            item.id != callback_data.cart_item_id for item in cart.items
        ):
            await _update_cart_view(callback, db, callback.from_user.id)
            return

        if result is None and cart is None:
            await _update_cart_view(callback, db, callback.from_user.id)
            return

        if result is None:
            if callback.message is not None:
                await callback.message.edit_text(ITEM_NOT_FOUND_TEXT)
            await callback.answer()
            return

        await _update_cart_view(callback, db, callback.from_user.id)
    except SQLAlchemyError:
        logger.exception("Database error while decreasing cart_item_id=%s", callback_data.cart_item_id)
        if callback.message is not None:
            await callback.message.edit_text(CART_UPDATE_ERROR_TEXT)
        await callback.answer()


@router.callback_query(CartCallback.filter(F.action == REMOVE_ACTION))
async def remove_item(
    callback: CallbackQuery,
    callback_data: CartCallback,
    db: AsyncSession,
) -> None:
    try:
        removed = await remove_cart_item(db, callback_data.cart_item_id)
        if not removed:
            if callback.message is not None:
                await callback.message.edit_text(ITEM_NOT_FOUND_TEXT)
            await callback.answer()
            return

        await _update_cart_view(callback, db, callback.from_user.id)
    except SQLAlchemyError:
        logger.exception("Database error while removing cart_item_id=%s", callback_data.cart_item_id)
        if callback.message is not None:
            await callback.message.edit_text(CART_UPDATE_ERROR_TEXT)
        await callback.answer()
