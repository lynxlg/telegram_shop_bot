from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
import pytest

from app.bot import create_bot, create_dispatcher


@pytest.mark.asyncio
async def test_create_bot() -> None:
    bot = create_bot()

    try:
        assert isinstance(bot, Bot)
        assert bot.default.parse_mode == ParseMode.HTML
    finally:
        await bot.session.close()


def test_create_dispatcher() -> None:
    dispatcher = create_dispatcher()

    assert isinstance(dispatcher, Dispatcher)
