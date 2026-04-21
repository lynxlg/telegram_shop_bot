import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.callbacks.admin_catalog import (
    BACK_TO_CATEGORY_ACTION,
    BACK_TO_ROOT_ACTION,
    DELETE_CATEGORY_ACTION,
    DELETE_PRODUCT_ACTION,
    OPEN_CATEGORY_ACTION,
    OPEN_PRODUCT_ACTION,
    START_CREATE_CATEGORY_ACTION,
    START_CREATE_PRODUCT_ACTION,
    START_EDIT_CATEGORY_ACTION,
    START_EDIT_PRODUCT_ACTION,
    TOGGLE_PRODUCT_ACTIVE_ACTION,
    AdminCatalogCallback,
)
from app.keyboards.admin_catalog import (
    build_admin_category_keyboard,
    build_admin_product_keyboard,
)
from app.models.user import User
from app.services.admin_catalog_text import (
    format_admin_category_text,
    format_admin_product_text,
    format_admin_root_text,
)
from app.services.catalog_admin import (
    CategoryHasChildrenError,
    CategoryHasProductsError,
    EmptyRequiredFieldError,
    InvalidBooleanValueError,
    InvalidPriceError,
    NonLeafCategoryError,
    create_category,
    create_product,
    delete_category,
    delete_product,
    get_admin_categories,
    get_admin_products_by_category,
    get_category_by_id,
    get_product_by_id,
    parse_is_active,
    parse_price,
    set_product_active,
    update_category_name,
    update_product_description,
    update_product_image_url,
    update_product_name,
    update_product_price,
)
from app.ui_text import get_ui_text

logger = logging.getLogger(__name__)
router = Router()

ADMIN_CATALOG_BUTTON_TEXT = get_ui_text("main_menu", "admin_catalog_button")
ADMIN_ACCESS_DENIED_TEXT = get_ui_text("admin_catalog", "access_denied")
ADMIN_LOAD_ERROR_TEXT = get_ui_text("admin_catalog", "load_error")
ADMIN_CATEGORY_NOT_FOUND_TEXT = get_ui_text("admin_catalog", "category_not_found")
ADMIN_PRODUCT_NOT_FOUND_TEXT = get_ui_text("admin_catalog", "product_not_found")
ADMIN_CATEGORY_CREATED_TEXT = get_ui_text("admin_catalog", "category_created")
ADMIN_CATEGORY_UPDATED_TEXT = get_ui_text("admin_catalog", "category_updated")
ADMIN_CATEGORY_DELETED_TEXT = get_ui_text("admin_catalog", "category_deleted")
ADMIN_PRODUCT_CREATED_TEXT = get_ui_text("admin_catalog", "product_created")
ADMIN_PRODUCT_UPDATED_TEXT = get_ui_text("admin_catalog", "product_updated")
ADMIN_PRODUCT_DELETED_TEXT = get_ui_text("admin_catalog", "product_deleted")
ADMIN_PRODUCT_ACTIVITY_UPDATED_TEXT = get_ui_text("admin_catalog", "product_activity_updated")
ADMIN_INVALID_NAME_TEXT = get_ui_text("admin_catalog", "invalid_name")
ADMIN_INVALID_PRICE_TEXT = get_ui_text("admin_catalog", "invalid_price")
ADMIN_INVALID_IS_ACTIVE_TEXT = get_ui_text("admin_catalog", "invalid_is_active")
ADMIN_CATEGORY_DELETE_HAS_CHILDREN_TEXT = get_ui_text(
    "admin_catalog", "category_delete_has_children"
)
ADMIN_CATEGORY_DELETE_HAS_PRODUCTS_TEXT = get_ui_text(
    "admin_catalog", "category_delete_has_products"
)
ADMIN_CATEGORY_CREATE_PARENT_HAS_PRODUCTS_TEXT = get_ui_text(
    "admin_catalog", "category_create_parent_has_products"
)
ADMIN_PRODUCT_REQUIRES_LEAF_TEXT = get_ui_text("admin_catalog", "product_requires_leaf_category")
ADMIN_CANCELLED_TEXT = get_ui_text("admin_catalog", "cancelled")
ADMIN_CANCEL_BUTTON_TEXT = get_ui_text("checkout", "cancel_button")
PROMPT_CREATE_ROOT_CATEGORY_TEXT = get_ui_text("admin_catalog", "prompt_create_root_category")
PROMPT_CREATE_SUBCATEGORY_TEXT = get_ui_text("admin_catalog", "prompt_create_subcategory")
PROMPT_EDIT_CATEGORY_TEXT = get_ui_text("admin_catalog", "prompt_edit_category")
PROMPT_PRODUCT_NAME_TEXT = get_ui_text("admin_catalog", "prompt_product_name")
PROMPT_PRODUCT_PRICE_TEXT = get_ui_text("admin_catalog", "prompt_product_price")
PROMPT_PRODUCT_DESCRIPTION_TEXT = get_ui_text("admin_catalog", "prompt_product_description")
PROMPT_PRODUCT_IMAGE_URL_TEXT = get_ui_text("admin_catalog", "prompt_product_image_url")
PROMPT_PRODUCT_IS_ACTIVE_TEXT = get_ui_text("admin_catalog", "prompt_product_is_active")
PROMPT_EDIT_NAME_TEXT = get_ui_text("admin_catalog", "prompt_edit_name")
PROMPT_EDIT_PRICE_TEXT = get_ui_text("admin_catalog", "prompt_edit_price")
PROMPT_EDIT_DESCRIPTION_TEXT = get_ui_text("admin_catalog", "prompt_edit_description")
PROMPT_EDIT_IMAGE_URL_TEXT = get_ui_text("admin_catalog", "prompt_edit_image_url")

ADMIN_ROLES = {"admin"}


class AdminCatalogStates(StatesGroup):
    waiting_for_category_name = State()
    waiting_for_product_name = State()
    waiting_for_product_price = State()
    waiting_for_product_description = State()
    waiting_for_product_image_url = State()
    waiting_for_product_is_active = State()
    waiting_for_product_edit_value = State()


async def _get_user_role(db: AsyncSession, telegram_id: int) -> str | None:
    result = await db.execute(select(User.role).where(User.telegram_id == telegram_id))
    return result.scalar_one_or_none()


async def _is_admin(db: AsyncSession, telegram_id: int) -> bool:
    role = await _get_user_role(db, telegram_id)
    return role in ADMIN_ROLES


async def _send_screen(target: Message | CallbackQuery, text: str, reply_markup=None) -> None:
    if not hasattr(target, "message"):
        await target.answer(text, reply_markup=reply_markup)
        return

    if target.message is None:
        await target.answer()
        return

    await target.message.edit_text(text, reply_markup=reply_markup)
    await target.answer()


async def _render_root_screen(target: Message | CallbackQuery, db: AsyncSession) -> None:
    categories = await get_admin_categories(db, None)
    await _send_screen(
        target,
        format_admin_root_text(categories),
        reply_markup=build_admin_category_keyboard(
            categories=categories,
            products=[],
            current_category_id=None,
            parent_category_id=None,
            can_add_product=False,
        ),
    )


async def _render_category_screen(
    target: Message | CallbackQuery,
    db: AsyncSession,
    category_id: int,
) -> None:
    category = await get_category_by_id(db, category_id)
    if category is None:
        await _send_screen(target, ADMIN_CATEGORY_NOT_FOUND_TEXT)
        return

    child_categories = await get_admin_categories(db, category.id)
    products = await get_admin_products_by_category(db, category.id)
    can_add_product = not child_categories

    await _send_screen(
        target,
        format_admin_category_text(category, child_categories, products, can_add_product),
        reply_markup=build_admin_category_keyboard(
            categories=child_categories,
            products=products,
            current_category_id=category.id,
            parent_category_id=category.parent_id,
            can_add_product=can_add_product,
        ),
    )


async def _render_product_screen(
    target: Message | CallbackQuery,
    db: AsyncSession,
    product_id: int,
) -> None:
    product = await get_product_by_id(db, product_id)
    if product is None:
        await _send_screen(target, ADMIN_PRODUCT_NOT_FOUND_TEXT)
        return

    await _send_screen(
        target,
        format_admin_product_text(product),
        reply_markup=build_admin_product_keyboard(
            product_id=product.id,
            category_id=product.category_id,
            is_active=product.is_active,
        ),
    )


async def _cancel_state_and_return(message: Message, state: FSMContext, db: AsyncSession) -> None:
    state_data = await state.get_data()
    await state.clear()
    await message.answer(ADMIN_CANCELLED_TEXT)

    return_product_id = state_data.get("return_product_id")
    return_category_id = state_data.get("return_category_id")
    if return_product_id is not None:
        await _render_product_screen(message, db, return_product_id)
        return
    if return_category_id is not None:
        await _render_category_screen(message, db, return_category_id)
        return
    await _render_root_screen(message, db)


@router.message(AdminCatalogStates.waiting_for_category_name, F.text == ADMIN_CANCEL_BUTTON_TEXT)
@router.message(AdminCatalogStates.waiting_for_product_name, F.text == ADMIN_CANCEL_BUTTON_TEXT)
@router.message(AdminCatalogStates.waiting_for_product_price, F.text == ADMIN_CANCEL_BUTTON_TEXT)
@router.message(
    AdminCatalogStates.waiting_for_product_description, F.text == ADMIN_CANCEL_BUTTON_TEXT
)
@router.message(
    AdminCatalogStates.waiting_for_product_image_url, F.text == ADMIN_CANCEL_BUTTON_TEXT
)
@router.message(
    AdminCatalogStates.waiting_for_product_is_active, F.text == ADMIN_CANCEL_BUTTON_TEXT
)
@router.message(
    AdminCatalogStates.waiting_for_product_edit_value, F.text == ADMIN_CANCEL_BUTTON_TEXT
)
async def cancel_admin_action(message: Message, state: FSMContext, db: AsyncSession) -> None:
    telegram_user = message.from_user
    if telegram_user is None:
        await state.clear()
        await message.answer(ADMIN_CANCELLED_TEXT)
        return
    await _cancel_state_and_return(message, state, db)


@router.message(F.text == ADMIN_CATALOG_BUTTON_TEXT)
async def open_admin_catalog(message: Message, db: AsyncSession) -> None:
    telegram_user = message.from_user
    if telegram_user is None:
        await message.answer(ADMIN_LOAD_ERROR_TEXT)
        return

    try:
        if not await _is_admin(db, telegram_user.id):
            await message.answer(ADMIN_ACCESS_DENIED_TEXT)
            return
        await _render_root_screen(message, db)
    except SQLAlchemyError:
        logger.exception(
            "Database error while opening admin catalog telegram_id=%s", telegram_user.id
        )
        await message.answer(ADMIN_LOAD_ERROR_TEXT)


@router.callback_query(AdminCatalogCallback.filter(F.action == BACK_TO_ROOT_ACTION))
async def back_to_admin_root(callback: CallbackQuery, db: AsyncSession) -> None:
    try:
        if not await _is_admin(db, callback.from_user.id):
            await callback.answer(ADMIN_ACCESS_DENIED_TEXT, show_alert=True)
            return
        await _render_root_screen(callback, db)
    except SQLAlchemyError:
        logger.exception(
            "Database error while returning to admin root telegram_id=%s", callback.from_user.id
        )
        if callback.message is not None:
            await callback.message.edit_text(ADMIN_LOAD_ERROR_TEXT)
        await callback.answer()


@router.callback_query(AdminCatalogCallback.filter(F.action == OPEN_CATEGORY_ACTION))
@router.callback_query(AdminCatalogCallback.filter(F.action == BACK_TO_CATEGORY_ACTION))
async def open_admin_category(
    callback: CallbackQuery,
    callback_data: AdminCatalogCallback,
    db: AsyncSession,
) -> None:
    try:
        if not await _is_admin(db, callback.from_user.id):
            await callback.answer(ADMIN_ACCESS_DENIED_TEXT, show_alert=True)
            return
        if callback_data.category_id is None:
            await callback.answer()
            return
        await _render_category_screen(callback, db, callback_data.category_id)
    except SQLAlchemyError:
        logger.exception(
            "Database error while opening admin category telegram_id=%s category_id=%s",
            callback.from_user.id,
            callback_data.category_id,
        )
        if callback.message is not None:
            await callback.message.edit_text(ADMIN_LOAD_ERROR_TEXT)
        await callback.answer()


@router.callback_query(AdminCatalogCallback.filter(F.action == OPEN_PRODUCT_ACTION))
async def open_admin_product(
    callback: CallbackQuery,
    callback_data: AdminCatalogCallback,
    db: AsyncSession,
) -> None:
    try:
        if not await _is_admin(db, callback.from_user.id):
            await callback.answer(ADMIN_ACCESS_DENIED_TEXT, show_alert=True)
            return
        if callback_data.product_id is None:
            await callback.answer()
            return
        await _render_product_screen(callback, db, callback_data.product_id)
    except SQLAlchemyError:
        logger.exception(
            "Database error while opening admin product telegram_id=%s product_id=%s",
            callback.from_user.id,
            callback_data.product_id,
        )
        if callback.message is not None:
            await callback.message.edit_text(ADMIN_LOAD_ERROR_TEXT)
        await callback.answer()


@router.callback_query(AdminCatalogCallback.filter(F.action == START_CREATE_CATEGORY_ACTION))
async def start_create_category(
    callback: CallbackQuery,
    callback_data: AdminCatalogCallback,
    state: FSMContext,
    db: AsyncSession,
) -> None:
    try:
        if not await _is_admin(db, callback.from_user.id):
            await callback.answer(ADMIN_ACCESS_DENIED_TEXT, show_alert=True)
            return

        await state.set_state(AdminCatalogStates.waiting_for_category_name)
        await state.update_data(
            mode="create_category",
            parent_category_id=callback_data.category_id,
            return_category_id=callback_data.category_id,
        )
        prompt = (
            PROMPT_CREATE_SUBCATEGORY_TEXT
            if callback_data.category_id is not None
            else PROMPT_CREATE_ROOT_CATEGORY_TEXT
        )
        if callback.message is not None:
            await callback.message.answer(prompt)
        await callback.answer()
    except SQLAlchemyError:
        logger.exception(
            "Database error while starting category create telegram_id=%s parent_category_id=%s",
            callback.from_user.id,
            callback_data.category_id,
        )
        if callback.message is not None:
            await callback.message.answer(ADMIN_LOAD_ERROR_TEXT)
        await callback.answer()


@router.callback_query(AdminCatalogCallback.filter(F.action == START_EDIT_CATEGORY_ACTION))
async def start_edit_category(
    callback: CallbackQuery,
    callback_data: AdminCatalogCallback,
    state: FSMContext,
    db: AsyncSession,
) -> None:
    try:
        if not await _is_admin(db, callback.from_user.id):
            await callback.answer(ADMIN_ACCESS_DENIED_TEXT, show_alert=True)
            return
        if callback_data.category_id is None:
            await callback.answer()
            return

        await state.set_state(AdminCatalogStates.waiting_for_category_name)
        await state.update_data(
            mode="edit_category",
            category_id=callback_data.category_id,
            return_category_id=callback_data.category_id,
        )
        if callback.message is not None:
            await callback.message.answer(PROMPT_EDIT_CATEGORY_TEXT)
        await callback.answer()
    except SQLAlchemyError:
        logger.exception(
            "Database error while starting category rename telegram_id=%s category_id=%s",
            callback.from_user.id,
            callback_data.category_id,
        )
        if callback.message is not None:
            await callback.message.answer(ADMIN_LOAD_ERROR_TEXT)
        await callback.answer()


@router.message(AdminCatalogStates.waiting_for_category_name)
async def receive_category_name(message: Message, state: FSMContext, db: AsyncSession) -> None:
    telegram_user = message.from_user
    if telegram_user is None:
        await state.clear()
        await message.answer(ADMIN_LOAD_ERROR_TEXT)
        return

    try:
        if not await _is_admin(db, telegram_user.id):
            await state.clear()
            await message.answer(ADMIN_ACCESS_DENIED_TEXT)
            return

        if not message.text:
            await message.answer(ADMIN_INVALID_NAME_TEXT)
            return

        state_data = await state.get_data()
        mode = state_data.get("mode")

        if mode == "create_category":
            created_category = await create_category(
                db,
                message.text,
                parent_id=state_data.get("parent_category_id"),
            )
            if created_category is None:
                await state.clear()
                await message.answer(ADMIN_CATEGORY_NOT_FOUND_TEXT)
                await _render_root_screen(message, db)
                return

            await state.clear()
            await message.answer(ADMIN_CATEGORY_CREATED_TEXT)
            if created_category.parent_id is None:
                await _render_root_screen(message, db)
            else:
                await _render_category_screen(message, db, created_category.parent_id)
            return

        if mode == "edit_category":
            category_id = state_data.get("category_id")
            if category_id is None:
                await state.clear()
                await message.answer(ADMIN_CATEGORY_NOT_FOUND_TEXT)
                return

            updated_category = await update_category_name(db, category_id, message.text)
            if updated_category is None:
                await state.clear()
                await message.answer(ADMIN_CATEGORY_NOT_FOUND_TEXT)
                await _render_root_screen(message, db)
                return

            await state.clear()
            await message.answer(ADMIN_CATEGORY_UPDATED_TEXT)
            await _render_category_screen(message, db, updated_category.id)
            return

        await state.clear()
        await message.answer(ADMIN_LOAD_ERROR_TEXT)
    except EmptyRequiredFieldError:
        await message.answer(ADMIN_INVALID_NAME_TEXT)
    except CategoryHasProductsError:
        return_category_id = (await state.get_data()).get("return_category_id")
        await state.clear()
        await message.answer(ADMIN_CATEGORY_CREATE_PARENT_HAS_PRODUCTS_TEXT)
        if return_category_id is not None:
            await _render_category_screen(message, db, return_category_id)
        else:
            await _render_root_screen(message, db)
    except SQLAlchemyError:
        await state.clear()
        logger.exception(
            "Database error while processing category name telegram_id=%s", telegram_user.id
        )
        await message.answer(ADMIN_LOAD_ERROR_TEXT)


@router.callback_query(AdminCatalogCallback.filter(F.action == DELETE_CATEGORY_ACTION))
async def remove_category(
    callback: CallbackQuery,
    callback_data: AdminCatalogCallback,
    db: AsyncSession,
) -> None:
    try:
        if not await _is_admin(db, callback.from_user.id):
            await callback.answer(ADMIN_ACCESS_DENIED_TEXT, show_alert=True)
            return
        if callback_data.category_id is None:
            await callback.answer()
            return

        category = await get_category_by_id(db, callback_data.category_id)
        if category is None:
            await callback.answer(ADMIN_CATEGORY_NOT_FOUND_TEXT, show_alert=True)
            return

        parent_id = category.parent_id
        deleted = await delete_category(db, category.id)
        if not deleted:
            await callback.answer(ADMIN_CATEGORY_NOT_FOUND_TEXT, show_alert=True)
            return

        if parent_id is None:
            await _render_root_screen(callback, db)
        else:
            await _render_category_screen(callback, db, parent_id)
    except CategoryHasChildrenError:
        await callback.answer(ADMIN_CATEGORY_DELETE_HAS_CHILDREN_TEXT, show_alert=True)
    except CategoryHasProductsError:
        await callback.answer(ADMIN_CATEGORY_DELETE_HAS_PRODUCTS_TEXT, show_alert=True)
    except SQLAlchemyError:
        logger.exception(
            "Database error while deleting category telegram_id=%s category_id=%s",
            callback.from_user.id,
            callback_data.category_id,
        )
        if callback.message is not None:
            await callback.message.edit_text(ADMIN_LOAD_ERROR_TEXT)
        await callback.answer()


@router.callback_query(AdminCatalogCallback.filter(F.action == START_CREATE_PRODUCT_ACTION))
async def start_create_product(
    callback: CallbackQuery,
    callback_data: AdminCatalogCallback,
    state: FSMContext,
    db: AsyncSession,
) -> None:
    try:
        if not await _is_admin(db, callback.from_user.id):
            await callback.answer(ADMIN_ACCESS_DENIED_TEXT, show_alert=True)
            return
        if callback_data.category_id is None:
            await callback.answer()
            return

        await state.set_state(AdminCatalogStates.waiting_for_product_name)
        await state.update_data(
            mode="create_product",
            category_id=callback_data.category_id,
            return_category_id=callback_data.category_id,
        )
        if callback.message is not None:
            await callback.message.answer(PROMPT_PRODUCT_NAME_TEXT)
        await callback.answer()
    except SQLAlchemyError:
        logger.exception(
            "Database error while starting product create telegram_id=%s category_id=%s",
            callback.from_user.id,
            callback_data.category_id,
        )
        if callback.message is not None:
            await callback.message.answer(ADMIN_LOAD_ERROR_TEXT)
        await callback.answer()


@router.message(AdminCatalogStates.waiting_for_product_name)
async def receive_product_name(message: Message, state: FSMContext, db: AsyncSession) -> None:
    telegram_user = message.from_user
    if telegram_user is None:
        await state.clear()
        await message.answer(ADMIN_LOAD_ERROR_TEXT)
        return

    try:
        if not await _is_admin(db, telegram_user.id):
            await state.clear()
            await message.answer(ADMIN_ACCESS_DENIED_TEXT)
            return
        if not message.text:
            await message.answer(ADMIN_INVALID_NAME_TEXT)
            return

        update_product_name_value = message.text.strip()
        if not update_product_name_value:
            await message.answer(ADMIN_INVALID_NAME_TEXT)
            return

        await state.update_data(product_name=update_product_name_value)
        await state.set_state(AdminCatalogStates.waiting_for_product_price)
        await message.answer(PROMPT_PRODUCT_PRICE_TEXT)
    except SQLAlchemyError:
        await state.clear()
        logger.exception(
            "Database error while receiving product name telegram_id=%s", telegram_user.id
        )
        await message.answer(ADMIN_LOAD_ERROR_TEXT)


@router.message(AdminCatalogStates.waiting_for_product_price)
async def receive_product_price(message: Message, state: FSMContext, db: AsyncSession) -> None:
    telegram_user = message.from_user
    if telegram_user is None:
        await state.clear()
        await message.answer(ADMIN_LOAD_ERROR_TEXT)
        return

    try:
        if not await _is_admin(db, telegram_user.id):
            await state.clear()
            await message.answer(ADMIN_ACCESS_DENIED_TEXT)
            return
        if not message.text:
            await message.answer(ADMIN_INVALID_PRICE_TEXT)
            return

        price = parse_price(message.text)
        await state.update_data(product_price=str(price))
        await state.set_state(AdminCatalogStates.waiting_for_product_description)
        await message.answer(PROMPT_PRODUCT_DESCRIPTION_TEXT)
    except InvalidPriceError:
        await message.answer(ADMIN_INVALID_PRICE_TEXT)
    except SQLAlchemyError:
        await state.clear()
        logger.exception(
            "Database error while receiving product price telegram_id=%s", telegram_user.id
        )
        await message.answer(ADMIN_LOAD_ERROR_TEXT)


@router.message(AdminCatalogStates.waiting_for_product_description)
async def receive_product_description(
    message: Message, state: FSMContext, db: AsyncSession
) -> None:
    telegram_user = message.from_user
    if telegram_user is None:
        await state.clear()
        await message.answer(ADMIN_LOAD_ERROR_TEXT)
        return

    try:
        if not await _is_admin(db, telegram_user.id):
            await state.clear()
            await message.answer(ADMIN_ACCESS_DENIED_TEXT)
            return

        await state.update_data(product_description=message.text or "")
        await state.set_state(AdminCatalogStates.waiting_for_product_image_url)
        await message.answer(PROMPT_PRODUCT_IMAGE_URL_TEXT)
    except SQLAlchemyError:
        await state.clear()
        logger.exception(
            "Database error while receiving product description telegram_id=%s", telegram_user.id
        )
        await message.answer(ADMIN_LOAD_ERROR_TEXT)


@router.message(AdminCatalogStates.waiting_for_product_image_url)
async def receive_product_image_url(message: Message, state: FSMContext, db: AsyncSession) -> None:
    telegram_user = message.from_user
    if telegram_user is None:
        await state.clear()
        await message.answer(ADMIN_LOAD_ERROR_TEXT)
        return

    try:
        if not await _is_admin(db, telegram_user.id):
            await state.clear()
            await message.answer(ADMIN_ACCESS_DENIED_TEXT)
            return

        await state.update_data(product_image_url=message.text or "")
        await state.set_state(AdminCatalogStates.waiting_for_product_is_active)
        await message.answer(PROMPT_PRODUCT_IS_ACTIVE_TEXT)
    except SQLAlchemyError:
        await state.clear()
        logger.exception(
            "Database error while receiving product image url telegram_id=%s", telegram_user.id
        )
        await message.answer(ADMIN_LOAD_ERROR_TEXT)


@router.message(AdminCatalogStates.waiting_for_product_is_active)
async def receive_product_is_active(message: Message, state: FSMContext, db: AsyncSession) -> None:
    telegram_user = message.from_user
    if telegram_user is None:
        await state.clear()
        await message.answer(ADMIN_LOAD_ERROR_TEXT)
        return

    try:
        if not await _is_admin(db, telegram_user.id):
            await state.clear()
            await message.answer(ADMIN_ACCESS_DENIED_TEXT)
            return
        if not message.text:
            await message.answer(ADMIN_INVALID_IS_ACTIVE_TEXT)
            return

        is_active = parse_is_active(message.text)
        state_data = await state.get_data()
        category_id = state_data.get("category_id")
        if category_id is None:
            await state.clear()
            await message.answer(ADMIN_CATEGORY_NOT_FOUND_TEXT)
            await _render_root_screen(message, db)
            return

        created_product = await create_product(
            db,
            category_id=category_id,
            name=state_data.get("product_name", ""),
            price=parse_price(state_data.get("product_price", "")),
            description=state_data.get("product_description"),
            image_url=state_data.get("product_image_url"),
            is_active=is_active,
        )
        if created_product is None:
            await state.clear()
            await message.answer(ADMIN_CATEGORY_NOT_FOUND_TEXT)
            await _render_root_screen(message, db)
            return

        await state.clear()
        await message.answer(ADMIN_PRODUCT_CREATED_TEXT)
        await _render_category_screen(message, db, category_id)
    except InvalidBooleanValueError:
        await message.answer(ADMIN_INVALID_IS_ACTIVE_TEXT)
    except InvalidPriceError:
        await state.clear()
        await message.answer(ADMIN_INVALID_PRICE_TEXT)
    except NonLeafCategoryError:
        return_category_id = (await state.get_data()).get("return_category_id")
        await state.clear()
        await message.answer(ADMIN_PRODUCT_REQUIRES_LEAF_TEXT)
        if return_category_id is not None:
            await _render_category_screen(message, db, return_category_id)
    except SQLAlchemyError:
        await state.clear()
        logger.exception("Database error while creating product telegram_id=%s", telegram_user.id)
        await message.answer(ADMIN_LOAD_ERROR_TEXT)


@router.callback_query(AdminCatalogCallback.filter(F.action == START_EDIT_PRODUCT_ACTION))
async def start_edit_product(
    callback: CallbackQuery,
    callback_data: AdminCatalogCallback,
    state: FSMContext,
    db: AsyncSession,
) -> None:
    try:
        if not await _is_admin(db, callback.from_user.id):
            await callback.answer(ADMIN_ACCESS_DENIED_TEXT, show_alert=True)
            return
        if callback_data.product_id is None or callback_data.field is None:
            await callback.answer()
            return

        prompt_map = {
            "name": PROMPT_EDIT_NAME_TEXT,
            "price": PROMPT_EDIT_PRICE_TEXT,
            "description": PROMPT_EDIT_DESCRIPTION_TEXT,
            "image_url": PROMPT_EDIT_IMAGE_URL_TEXT,
        }
        prompt = prompt_map.get(callback_data.field)
        if prompt is None:
            await callback.answer()
            return

        await state.set_state(AdminCatalogStates.waiting_for_product_edit_value)
        await state.update_data(
            mode="edit_product",
            product_id=callback_data.product_id,
            field=callback_data.field,
            return_product_id=callback_data.product_id,
        )
        if callback.message is not None:
            await callback.message.answer(prompt)
        await callback.answer()
    except SQLAlchemyError:
        logger.exception(
            "Database error while starting product edit telegram_id=%s product_id=%s field=%s",
            callback.from_user.id,
            callback_data.product_id,
            callback_data.field,
        )
        if callback.message is not None:
            await callback.message.answer(ADMIN_LOAD_ERROR_TEXT)
        await callback.answer()


@router.message(AdminCatalogStates.waiting_for_product_edit_value)
async def receive_product_edit_value(message: Message, state: FSMContext, db: AsyncSession) -> None:
    telegram_user = message.from_user
    if telegram_user is None:
        await state.clear()
        await message.answer(ADMIN_LOAD_ERROR_TEXT)
        return

    try:
        if not await _is_admin(db, telegram_user.id):
            await state.clear()
            await message.answer(ADMIN_ACCESS_DENIED_TEXT)
            return

        state_data = await state.get_data()
        product_id = state_data.get("product_id")
        field = state_data.get("field")
        if product_id is None or field is None:
            await state.clear()
            await message.answer(ADMIN_PRODUCT_NOT_FOUND_TEXT)
            return

        if field == "name":
            if not message.text:
                await message.answer(ADMIN_INVALID_NAME_TEXT)
                return
            product = await update_product_name(db, product_id, message.text)
        elif field == "price":
            if not message.text:
                await message.answer(ADMIN_INVALID_PRICE_TEXT)
                return
            product = await update_product_price(db, product_id, parse_price(message.text))
        elif field == "description":
            product = await update_product_description(db, product_id, message.text or "")
        elif field == "image_url":
            product = await update_product_image_url(db, product_id, message.text or "")
        else:
            await state.clear()
            await message.answer(ADMIN_LOAD_ERROR_TEXT)
            return

        if product is None:
            await state.clear()
            await message.answer(ADMIN_PRODUCT_NOT_FOUND_TEXT)
            await _render_root_screen(message, db)
            return

        await state.clear()
        await message.answer(ADMIN_PRODUCT_UPDATED_TEXT)
        await _render_product_screen(message, db, product.id)
    except EmptyRequiredFieldError:
        await message.answer(ADMIN_INVALID_NAME_TEXT)
    except InvalidPriceError:
        await message.answer(ADMIN_INVALID_PRICE_TEXT)
    except SQLAlchemyError:
        await state.clear()
        logger.exception("Database error while editing product telegram_id=%s", telegram_user.id)
        await message.answer(ADMIN_LOAD_ERROR_TEXT)


@router.callback_query(AdminCatalogCallback.filter(F.action == TOGGLE_PRODUCT_ACTIVE_ACTION))
async def toggle_admin_product_active(
    callback: CallbackQuery,
    callback_data: AdminCatalogCallback,
    db: AsyncSession,
) -> None:
    try:
        if not await _is_admin(db, callback.from_user.id):
            await callback.answer(ADMIN_ACCESS_DENIED_TEXT, show_alert=True)
            return
        if callback_data.product_id is None:
            await callback.answer()
            return

        product = await get_product_by_id(db, callback_data.product_id)
        if product is None:
            await callback.answer(ADMIN_PRODUCT_NOT_FOUND_TEXT, show_alert=True)
            return

        updated_product = await set_product_active(db, product.id, not product.is_active)
        if updated_product is None:
            await callback.answer(ADMIN_PRODUCT_NOT_FOUND_TEXT, show_alert=True)
            return

        await _render_product_screen(callback, db, updated_product.id)
    except SQLAlchemyError:
        logger.exception(
            "Database error while toggling product telegram_id=%s product_id=%s",
            callback.from_user.id,
            callback_data.product_id,
        )
        if callback.message is not None:
            await callback.message.edit_text(ADMIN_LOAD_ERROR_TEXT)
        await callback.answer()


@router.callback_query(AdminCatalogCallback.filter(F.action == DELETE_PRODUCT_ACTION))
async def remove_product(
    callback: CallbackQuery,
    callback_data: AdminCatalogCallback,
    db: AsyncSession,
) -> None:
    try:
        if not await _is_admin(db, callback.from_user.id):
            await callback.answer(ADMIN_ACCESS_DENIED_TEXT, show_alert=True)
            return
        if callback_data.product_id is None:
            await callback.answer()
            return

        product = await get_product_by_id(db, callback_data.product_id)
        if product is None:
            await callback.answer(ADMIN_PRODUCT_NOT_FOUND_TEXT, show_alert=True)
            return

        category_id = product.category_id
        deleted = await delete_product(db, product.id)
        if not deleted:
            await callback.answer(ADMIN_PRODUCT_NOT_FOUND_TEXT, show_alert=True)
            return

        await _render_category_screen(callback, db, category_id)
    except SQLAlchemyError:
        logger.exception(
            "Database error while deleting product telegram_id=%s product_id=%s",
            callback.from_user.id,
            callback_data.product_id,
        )
        if callback.message is not None:
            await callback.message.edit_text(ADMIN_LOAD_ERROR_TEXT)
        await callback.answer()
