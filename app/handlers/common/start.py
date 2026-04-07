import logging
from datetime import datetime, timezone

from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.keyboards.main_menu import get_main_menu_keyboard
from app.models.user import User


logger = logging.getLogger(__name__)
router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, db: AsyncSession) -> None:
    telegram_user = message.from_user

    if telegram_user is None:
        logger.warning("Received /start without from_user payload")
        await message.answer("Не удалось определить пользователя.")
        return

    try:
        result = await db.execute(
            select(User).where(User.telegram_id == telegram_user.id)
        )
        user = result.scalar_one_or_none()
        now = datetime.now(timezone.utc)

        if user is None:
            user = User(
                telegram_id=telegram_user.id,
                username=telegram_user.username,
                first_name=telegram_user.first_name,
                last_name=telegram_user.last_name,
                role="user",
                last_activity=now,
            )
            db.add(user)
            await db.commit()
            logger.info("Registered new user telegram_id=%s", telegram_user.id)
        else:
            user.username = telegram_user.username
            user.first_name = telegram_user.first_name
            user.last_name = telegram_user.last_name
            user.last_activity = now
            await db.commit()
            logger.info("Updated last_activity for telegram_id=%s", telegram_user.id)

        await message.answer(
            f"Добро пожаловать, {telegram_user.first_name}! Бот запущен.",
            reply_markup=get_main_menu_keyboard(),
        )
    except SQLAlchemyError:
        await db.rollback()
        logger.exception(
            "Database error while processing /start for telegram_id=%s",
            telegram_user.id,
        )
        await message.answer(
            "Не удалось сохранить ваши данные. Попробуйте еще раз позже."
        )
