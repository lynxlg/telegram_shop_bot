import pytest
from pydantic import ValidationError

from app.config import Settings


def test_settings_load_from_env_file(monkeypatch) -> None:
    monkeypatch.delenv("BOT_TOKEN", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)

    settings = Settings(_env_file="tests/.env.test")

    assert settings.bot_token == "test_token_12345"
    assert "/shop_bot_test" in settings.database_url


def test_settings_use_default_values_when_env_file_missing(monkeypatch) -> None:
    monkeypatch.delenv("BOT_TOKEN", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)

    settings = Settings(_env_file=None)

    assert settings.bot_token == "TEST_BOT_TOKEN"
    assert settings.database_url.endswith("/telegram_shop_bot")


def test_settings_validate_empty_values() -> None:
    with pytest.raises(ValidationError):
        Settings(bot_token="", database_url="")
