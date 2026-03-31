import pytest
from pydantic import ValidationError

from app.config import Settings


def test_settings_load_from_env_file(test_settings) -> None:
    assert test_settings.bot_token == "test_token_12345"
    assert test_settings.database_url.endswith("/shop_bot_test")


def test_settings_use_default_values_when_env_file_missing() -> None:
    settings = Settings(_env_file=None)

    assert settings.bot_token == "TEST_BOT_TOKEN"
    assert settings.database_url.endswith("/telegram_shop_bot")


def test_settings_validate_empty_values() -> None:
    with pytest.raises(ValidationError):
        Settings(bot_token="", database_url="")
