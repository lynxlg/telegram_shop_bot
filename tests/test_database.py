import pytest
from sqlalchemy import inspect, select, text
from sqlalchemy.exc import IntegrityError

from app.models.user import User


@pytest.mark.asyncio
async def test_database_connection_successful(test_engine) -> None:
    async with test_engine.connect() as connection:
        result = await connection.execute(text("SELECT 1"))

    assert result.scalar_one() == 1


@pytest.mark.asyncio
async def test_tables_created(test_engine) -> None:
    async with test_engine.begin() as connection:
        tables = await connection.run_sync(
            lambda sync_connection: inspect(sync_connection).get_table_names()
        )

    assert "users" in tables


@pytest.mark.asyncio
async def test_user_persist_and_load(db_session) -> None:
    user = User(
        telegram_id=777000,
        username="persisted_user",
        first_name="Persisted",
        last_name="User",
    )

    db_session.add(user)
    await db_session.commit()

    result = await db_session.execute(
        select(User).where(User.telegram_id == 777000)
    )
    saved_user = result.scalar_one()

    assert saved_user.username == "persisted_user"
    assert saved_user.first_name == "Persisted"
    assert saved_user.last_name == "User"


@pytest.mark.asyncio
async def test_telegram_id_unique_constraint(db_session) -> None:
    first_user = User(
        telegram_id=100500,
        username="first_user",
        first_name="First",
        last_name="User",
    )
    second_user = User(
        telegram_id=100500,
        username="second_user",
        first_name="Second",
        last_name="User",
    )

    db_session.add(first_user)
    await db_session.commit()

    db_session.add(second_user)

    with pytest.raises(IntegrityError):
        await db_session.commit()

    await db_session.rollback()
