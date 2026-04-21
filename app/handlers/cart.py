import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.callbacks.cart import (
    CANCEL_CHECKOUT_ACTION,
    CONFIRM_ORDER_ACTION,
    DECREASE_ACTION,
    INCREASE_ACTION,
    REMOVE_ACTION,
    START_CHECKOUT_ACTION,
    CartCallback,
)
from app.keyboards.cart import (
    CHECKOUT_CANCEL_TEXT,
    build_cart_keyboard,
    build_checkout_address_keyboard,
    build_checkout_confirmation_keyboard,
    build_checkout_phone_keyboard,
)
from app.keyboards.main_menu import get_main_menu_keyboard
from app.models.user import User
from app.services.cart import (
    decrease_cart_item_quantity,
    get_cart_by_telegram_id,
    increase_cart_item_quantity,
    remove_cart_item,
)
from app.services.cart_text import (
    EMPTY_CART_TEXT,
    format_cart_text,
    format_checkout_confirmation_text,
    format_order_created_text,
)
from app.services.order import (
    EmptyCartError,
    InvalidAddressError,
    InvalidPhoneError,
    build_checkout_summary,
    create_order_from_cart,
    normalize_phone,
)
from app.ui_text import get_ui_text

logger = logging.getLogger(__name__)
router = Router()

ITEM_NOT_FOUND_TEXT = get_ui_text("cart", "item_not_found")
CART_UPDATE_ERROR_TEXT = get_ui_text("cart", "update_error")
CHECKOUT_ERROR_TEXT = get_ui_text("checkout", "error")
PHONE_PROMPT_TEXT = get_ui_text("checkout", "phone_prompt")
ADDRESS_PROMPT_TEXT = get_ui_text("checkout", "address_prompt")
INVALID_PHONE_TEXT = get_ui_text("checkout", "invalid_phone")
INVALID_ADDRESS_TEXT = get_ui_text("checkout", "invalid_address")
CHECKOUT_CANCELLED_TEXT = get_ui_text("checkout", "cancelled")
CART_BUTTON_TEXT = get_ui_text("main_menu", "cart_button")
CHECKOUT_CANCELLED_CALLBACK_TEXT = get_ui_text("checkout", "cancelled_callback")
CHECKOUT_MAIN_MENU_TEXT = get_ui_text("checkout", "main_menu_prompt")


class CheckoutStates(StatesGroup):
    waiting_for_phone = State()
    waiting_for_address = State()
    waiting_for_confirmation = State()


async def _get_user_phone(db: AsyncSession, telegram_id: int) -> str | None:
    result = await db.execute(select(User).where(User.telegram_id == telegram_id))
    user = result.scalar_one_or_none()
    if user is None:
        return None
    return user.phone


async def _get_user_role(db: AsyncSession, telegram_id: int) -> str:
    result = await db.execute(select(User.role).where(User.telegram_id == telegram_id))
    role = result.scalar_one_or_none()
    return role or "user"


async def _cancel_checkout(
    state: FSMContext,
    message: Message,
    db: AsyncSession,
    telegram_id: int,
) -> None:
    await state.clear()
    await message.answer(CHECKOUT_CANCELLED_TEXT, reply_markup=get_main_menu_keyboard())
    await _render_cart(message, db, telegram_id)


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


@router.message(F.text == CART_BUTTON_TEXT)
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


@router.callback_query(CartCallback.filter(F.action == START_CHECKOUT_ACTION))
async def start_checkout(
    callback: CallbackQuery,
    state: FSMContext,
    db: AsyncSession,
) -> None:
    try:
        cart = await get_cart_by_telegram_id(db, callback.from_user.id)
        if cart is None or not cart.items:
            if callback.message is not None:
                await callback.message.edit_text(EMPTY_CART_TEXT)
            await callback.answer()
            return

        saved_phone = await _get_user_phone(db, callback.from_user.id)
        await state.set_state(CheckoutStates.waiting_for_phone)
        await state.update_data(saved_phone=saved_phone)
        if callback.message is not None:
            await callback.message.answer(
                PHONE_PROMPT_TEXT,
                reply_markup=build_checkout_phone_keyboard(saved_phone),
            )
        await callback.answer()
    except SQLAlchemyError:
        logger.exception(
            "Database error while starting checkout telegram_id=%s", callback.from_user.id
        )
        if callback.message is not None:
            await callback.message.answer(CHECKOUT_ERROR_TEXT)
        await callback.answer()


@router.message(CheckoutStates.waiting_for_phone, F.text == CHECKOUT_CANCEL_TEXT)
@router.message(CheckoutStates.waiting_for_address, F.text == CHECKOUT_CANCEL_TEXT)
async def cancel_checkout_by_message(
    message: Message,
    state: FSMContext,
    db: AsyncSession,
) -> None:
    telegram_user = message.from_user
    if telegram_user is None:
        await state.clear()
        await message.answer(CHECKOUT_CANCELLED_TEXT, reply_markup=get_main_menu_keyboard())
        return

    await _cancel_checkout(state, message, db, telegram_user.id)


@router.message(CheckoutStates.waiting_for_phone)
async def receive_checkout_phone(
    message: Message,
    state: FSMContext,
    db: AsyncSession,
) -> None:
    telegram_user = message.from_user
    if telegram_user is None:
        await state.clear()
        await message.answer(CHECKOUT_ERROR_TEXT)
        return

    raw_phone = None
    if getattr(message, "contact", None) is not None:
        raw_phone = message.contact.phone_number
    elif message.text:
        raw_phone = message.text

    if not raw_phone:
        await message.answer(INVALID_PHONE_TEXT)
        return

    try:
        phone = normalize_phone(raw_phone)
    except InvalidPhoneError:
        saved_phone = await _get_user_phone(db, telegram_user.id)
        await message.answer(
            INVALID_PHONE_TEXT,
            reply_markup=build_checkout_phone_keyboard(saved_phone),
        )
        return

    await state.update_data(phone=phone)
    await state.set_state(CheckoutStates.waiting_for_address)
    await message.answer(
        ADDRESS_PROMPT_TEXT,
        reply_markup=build_checkout_address_keyboard(),
    )


@router.message(CheckoutStates.waiting_for_address)
async def receive_checkout_address(
    message: Message,
    state: FSMContext,
    db: AsyncSession,
) -> None:
    telegram_user = message.from_user
    if telegram_user is None:
        await state.clear()
        await message.answer(CHECKOUT_ERROR_TEXT)
        return

    if not message.text:
        await message.answer(INVALID_ADDRESS_TEXT, reply_markup=build_checkout_address_keyboard())
        return

    data = await state.get_data()
    phone = data.get("phone")
    if not phone:
        await state.clear()
        await message.answer(CHECKOUT_ERROR_TEXT, reply_markup=get_main_menu_keyboard())
        return

    try:
        cart = await get_cart_by_telegram_id(db, telegram_user.id)
        if cart is None or not cart.items:
            await state.clear()
            await message.answer(EMPTY_CART_TEXT, reply_markup=get_main_menu_keyboard())
            return

        summary = build_checkout_summary(cart, phone, message.text)
    except InvalidAddressError:
        await message.answer(
            INVALID_ADDRESS_TEXT,
            reply_markup=build_checkout_address_keyboard(),
        )
        return
    except InvalidPhoneError:
        await state.clear()
        await message.answer(CHECKOUT_ERROR_TEXT, reply_markup=get_main_menu_keyboard())
        return
    except SQLAlchemyError:
        logger.exception("Database error while preparing checkout telegram_id=%s", telegram_user.id)
        await state.clear()
        await message.answer(CHECKOUT_ERROR_TEXT, reply_markup=get_main_menu_keyboard())
        return

    await state.update_data(phone=summary.phone, shipping_address=summary.shipping_address)
    await state.set_state(CheckoutStates.waiting_for_confirmation)
    await message.answer(
        format_checkout_confirmation_text(cart, summary),
        reply_markup=build_checkout_confirmation_keyboard(),
    )


@router.callback_query(
    CheckoutStates.waiting_for_confirmation,
    CartCallback.filter(F.action == CONFIRM_ORDER_ACTION),
)
async def confirm_checkout(
    callback: CallbackQuery,
    state: FSMContext,
    db: AsyncSession,
) -> None:
    data = await state.get_data()
    phone = data.get("phone")
    shipping_address = data.get("shipping_address")
    if not phone or not shipping_address:
        await state.clear()
        if callback.message is not None:
            await callback.message.edit_text(CHECKOUT_ERROR_TEXT)
        await callback.answer()
        return

    try:
        order = await create_order_from_cart(
            db,
            callback.from_user.id,
            phone=phone,
            shipping_address=shipping_address,
        )
        role = await _get_user_role(db, callback.from_user.id)
        await state.clear()
        if callback.message is not None:
            await callback.message.edit_text(
                format_order_created_text(order.order_number),
                reply_markup=None,
            )
            await callback.message.answer(
                CHECKOUT_MAIN_MENU_TEXT,
                reply_markup=get_main_menu_keyboard(role),
            )
        await callback.answer()
    except EmptyCartError:
        await state.clear()
        if callback.message is not None:
            await callback.message.edit_text(EMPTY_CART_TEXT)
        await callback.answer()
    except (InvalidPhoneError, InvalidAddressError):
        await state.clear()
        if callback.message is not None:
            await callback.message.edit_text(CHECKOUT_ERROR_TEXT)
        await callback.answer()
    except SQLAlchemyError:
        logger.exception(
            "Database error while confirming checkout telegram_id=%s", callback.from_user.id
        )
        if callback.message is not None:
            await callback.message.edit_text(CHECKOUT_ERROR_TEXT)
        await callback.answer()


@router.callback_query(
    CheckoutStates.waiting_for_confirmation,
    CartCallback.filter(F.action == CANCEL_CHECKOUT_ACTION),
)
async def cancel_checkout_by_callback(
    callback: CallbackQuery,
    state: FSMContext,
    db: AsyncSession,
) -> None:
    await state.clear()
    if callback.message is not None:
        await _update_cart_view(callback, db, callback.from_user.id)
    await callback.answer(CHECKOUT_CANCELLED_CALLBACK_TEXT)


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
        logger.exception(
            "Database error while increasing cart_item_id=%s", callback_data.cart_item_id
        )
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
        if (
            result is None
            and cart is not None
            and all(item.id != callback_data.cart_item_id for item in cart.items)
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
        logger.exception(
            "Database error while decreasing cart_item_id=%s", callback_data.cart_item_id
        )
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
        logger.exception(
            "Database error while removing cart_item_id=%s", callback_data.cart_item_id
        )
        if callback.message is not None:
            await callback.message.edit_text(CART_UPDATE_ERROR_TEXT)
        await callback.answer()
