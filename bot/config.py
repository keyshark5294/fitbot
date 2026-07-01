"""Конфиг через pydantic-settings. Значения только из окружения/.env, ничего в коде."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    bot_token: str
    trainer_tg_id: int  # единственный тренер — его Telegram id (роль определяется этим)

    database_url: str  # postgresql+asyncpg://user:pass@host:5432/db
    redis_url: str | None = None  # для FSM; если пусто — MemoryStorage (dev)

    # YooKassa — Phase 0 заглушки, заполнишь при подключении платежей
    yookassa_shop_id: str | None = None
    yookassa_secret_key: str | None = None


settings = Settings()
