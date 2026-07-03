"""Конфиг через pydantic-settings. Значения только из окружения/.env, ничего в коде."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    bot_token: str
    trainer_tg_id: int  # тренер — её Telegram id; ей идут все уведомления
    admin_tg_id: int | None = None  # владелец — полный доступ как у тренера (см. IsTrainer)

    database_url: str  # postgresql+asyncpg://user:pass@host:5432/db
    redis_url: str | None = None  # для FSM; если пусто — MemoryStorage (dev)

    # Оплата — ручной сценарий (перевод на карту + подтверждение тренером).
    # Реквизиты тестовые; настоящие подставить в .env.
    payment_card: str = "0000 0000 0000 0000"
    payment_recipient: str = "Тест Тестович Т."


settings = Settings()
