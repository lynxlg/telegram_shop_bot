from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    bot_token: str = Field(default="TEST_BOT_TOKEN", min_length=1)
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/telegram_shop_bot",
        min_length=1,
    )
    yookassa_shop_id: str | None = Field(default=None)
    yookassa_secret_key: str | None = Field(default=None)
    yookassa_return_url: str = Field(default="https://example.com/yookassa/return", min_length=1)
    yookassa_webhook_host: str = Field(default="0.0.0.0", min_length=1)
    yookassa_webhook_port: int = Field(default=8080, ge=1, le=65535)
    yookassa_webhook_path: str = Field(default="/webhooks/yookassa", min_length=1)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
