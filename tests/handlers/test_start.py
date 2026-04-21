from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy import func, select

from app.handlers.common.start import cmd_start
from app.models.user import User


@pytest.mark.asyncio
async def test_start_registers_new_user(db_session, message_factory) -> None:
    message = message_factory()

    await cmd_start(message, db_session)

    result = await db_session.execute(select(User).where(User.telegram_id == message.from_user.id))
    user = result.scalar_one()

    assert user.username == "test_user"
    assert user.first_name == "Test"
    assert user.last_name == "User"
    message.answer.assert_awaited_once()
    assert "Добро пожаловать" in message.answer.await_args.args[0]
    reply_markup = message.answer.await_args.kwargs["reply_markup"]
    assert reply_markup.keyboard[0][0].text == "Каталог"
    assert reply_markup.keyboard[0][1].text == "Корзина"
    assert reply_markup.keyboard[1][0].text == "Статус заказа"
    assert len(reply_markup.keyboard) == 2


@pytest.mark.asyncio
async def test_start_updates_existing_user_without_duplicates(db_session, message_factory) -> None:
    old_time = datetime.now(timezone.utc) - timedelta(days=1)
    existing_user = User(
        telegram_id=123456789,
        username="old_user",
        first_name="Old",
        last_name="Name",
        last_activity=old_time,
    )
    db_session.add(existing_user)
    await db_session.commit()

    message = message_factory(username="new_user", first_name="New", last_name="Name")

    await cmd_start(message, db_session)

    count_result = await db_session.execute(
        select(func.count()).select_from(User).where(User.telegram_id == 123456789)
    )
    user_result = await db_session.execute(select(User).where(User.telegram_id == 123456789))
    updated_user = user_result.scalar_one()

    assert count_result.scalar_one() == 1
    assert updated_user.username == "new_user"
    assert updated_user.first_name == "New"
    assert updated_user.last_activity > old_time


@pytest.mark.asyncio
async def test_start_shows_operator_orders_button_for_operator_role(
    db_session,
    message_factory,
) -> None:
    existing_user = User(
        telegram_id=424242,
        username="operator_user",
        first_name="Op",
        last_name="Erator",
        role="operator",
    )
    db_session.add(existing_user)
    await db_session.commit()
    message = message_factory(telegram_id=424242, username="operator_user", first_name="Op")

    await cmd_start(message, db_session)

    reply_markup = message.answer.await_args.kwargs["reply_markup"]
    assert reply_markup.keyboard[2][0].text == "Заказы"
    assert len(reply_markup.keyboard) == 3


@pytest.mark.asyncio
async def test_start_shows_admin_catalog_button_for_admin_role(
    db_session,
    message_factory,
) -> None:
    existing_user = User(
        telegram_id=525252,
        username="admin_user",
        first_name="Admin",
        last_name="User",
        role="admin",
    )
    db_session.add(existing_user)
    await db_session.commit()
    message = message_factory(telegram_id=525252, username="admin_user", first_name="Admin")

    await cmd_start(message, db_session)

    reply_markup = message.answer.await_args.kwargs["reply_markup"]
    assert reply_markup.keyboard[2][0].text == "Заказы"
    assert reply_markup.keyboard[3][0].text == "Админ каталог"


@pytest.mark.asyncio
async def test_start_saves_all_user_fields(db_session, message_factory) -> None:
    message = message_factory(
        telegram_id=999111,
        username="field_user",
        first_name="Field",
        last_name="Tester",
    )

    await cmd_start(message, db_session)

    result = await db_session.execute(select(User).where(User.telegram_id == 999111))
    user = result.scalar_one()

    assert user.telegram_id == 999111
    assert user.username == "field_user"
    assert user.first_name == "Field"
    assert user.last_name == "Tester"
    assert user.role == "user"


@pytest.mark.asyncio
async def test_start_updates_last_activity_on_repeat(db_session, message_factory) -> None:
    initial_time = datetime.now(timezone.utc) - timedelta(hours=2)
    existing_user = User(
        telegram_id=321321,
        username="repeat_user",
        first_name="Repeat",
        last_name="User",
        last_activity=initial_time,
    )
    db_session.add(existing_user)
    await db_session.commit()

    message = message_factory(telegram_id=321321, username="repeat_user")

    await cmd_start(message, db_session)

    result = await db_session.execute(select(User).where(User.telegram_id == 321321))
    updated_user = result.scalar_one()

    assert updated_user.last_activity > initial_time


@pytest.mark.asyncio
async def test_start_handles_database_error(message_factory, db_error) -> None:
    message = message_factory()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None

    db_session = AsyncMock()
    db_session.execute = AsyncMock(return_value=mock_result)
    db_session.commit = AsyncMock(side_effect=db_error)
    db_session.rollback = AsyncMock()
    db_session.add = MagicMock()

    await cmd_start(message, db_session)

    db_session.rollback.assert_awaited_once()
    message.answer.assert_awaited_once()
    assert "Не удалось сохранить ваши данные" in message.answer.await_args.args[0]


@pytest.mark.asyncio
async def test_start_handles_missing_from_user() -> None:
    message = SimpleNamespace(from_user=None, answer=AsyncMock())
    db_session = AsyncMock()

    await cmd_start(message, db_session)

    message.answer.assert_awaited_once_with("Не удалось определить пользователя.")


@pytest.mark.asyncio
async def test_start_updates_existing_user_unit(message_factory) -> None:
    message = message_factory(username="updated_user", first_name="Updated")
    existing_user = User(
        telegram_id=message.from_user.id,
        username="old_user",
        first_name="Old",
        last_name="User",
        last_activity=datetime.now(timezone.utc) - timedelta(days=1),
    )
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = existing_user

    db_session = AsyncMock()
    db_session.execute = AsyncMock(return_value=mock_result)
    db_session.commit = AsyncMock()

    await cmd_start(message, db_session)

    db_session.commit.assert_awaited_once()
    assert existing_user.username == "updated_user"
    assert existing_user.first_name == "Updated"
    message.answer.assert_awaited_once()
