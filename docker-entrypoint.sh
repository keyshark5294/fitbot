#!/bin/sh
# Прогоняем миграции ДО старта бота (create_all не используем — только Alembic).
# DB уже готова: compose ждёт service_healthy для db.
set -e

echo "[entrypoint] alembic upgrade head"
alembic upgrade head

echo "[entrypoint] starting bot"
exec python -m bot
