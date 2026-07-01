# Fitness Coaching Bot

Телеграм-бот онлайн-сопровождения для одного тренера и его клиентов.
Один бот, ролевой доступ (тренер = `TRAINER_TG_ID`). aiogram 3 + PostgreSQL + Alembic.

## Стек
- aiogram 3 (один бот, тренер и клиенты разведены фильтром `IsTrainer`)
- PostgreSQL + SQLAlchemy 2.0 (async) + Alembic (миграции)
- Redis для FSM (опц.; без него — MemoryStorage)
- Планировщик напоминаний — единый минутный тикер (`bot/services/scheduler.py`)

## Быстрый старт
Нужен Python 3.12+ (проверено на 3.12 и 3.13).

```bash
python3 -m venv .venv && source .venv/bin/activate   # чтобы alembic/бот были в PATH
pip install -r requirements.txt

cp .env.example .env          # ОБЯЗАТЕЛЬНО. Без .env упадут и docker, и alembic.
# Впиши BOT_TOKEN и TRAINER_TG_ID. Остальное для локального запуска можно не трогать.
# Хосты БД/Redis стоят localhost — так и надо, когда alembic/бот запускаешь с машины;
# внутри docker compose сервис bot сам подменит их на db/redis.

docker compose up -d db redis # поднять базу и redis

# создать и применить первую миграцию (модели уже описаны):
alembic revision --autogenerate -m "initial"   # или: python -m alembic ...
alembic upgrade head

python -m bot                 # запуск бота (или: docker compose up bot)
```

### Если `port is already allocated` на 5432/6379
Значит порт занят другим Postgres/Redis. Посмотреть кем: `lsof -i :5432`.
Либо останови тот процесс, либо в `.env` поставь свободный порт (`DB_PORT=5433`)
и синхронно поправь порт в `DATABASE_URL` (`...@localhost:5433/...`).

## Структура
```
bot/
  __main__.py          entrypoint (python -m bot)
  config.py            настройки из .env (pydantic-settings)
  db/
    base.py models.py  ORM-модели (зеркалят schema.sql)
    engine.py          async-движок + пул
    repositories/      запросы к БД (base + clients как образец)
  middlewares/db.py    сессия БД в каждый хендлер
  filters/is_trainer.py
  handlers/
    client/  registration(готов /start) profile program checkin payment
    trainer/ review clients programs broadcast
  services/
    scheduler.py       минутный тикер напоминаний (логику дописать)
    payments.py        yookassa + фнс (перенос из ConnectAssist)
  utils/logging.py
migrations/            alembic
```

## Замечания
- `schema.sql` — эталонный DDL для чтения. Источник правды по миграциям — Alembic.
- Хендлеры (кроме `/start`) — заглушки с `TODO`: содержательную логику пишем отдельно.
