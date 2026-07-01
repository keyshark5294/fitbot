# CLAUDE.md — память проекта fitbot

Онлайн-сопровождение для **одного тренера** и её клиентов через Telegram-бота.
Позиционирование — инструмент под одного тренера. **SaaS/мультитенантность пока не делаем.**
Продукт вырос из старого проекта «Жимов»; цель — быстро собрать рабочий инструмент, а не учебник.

## Рабочий режим
- Владелец направляет архитектуру, код пишет агент. Перед правками — показывать дифф (**Ask before edits**), не включать авто-approve на важных изменениях.
- Объяснения — кратко и по делу; не превращать задачи в обучающий курс.
- Язык общения — русский.

## Стек (проверено, версии зафиксированы в requirements.txt)
- Python 3.13 (на маке). aiogram 3.13 — один бот, роли через фильтр.
- PostgreSQL 16 + SQLAlchemy 2.0 (async, `SQLAlchemy[asyncio]`) + Alembic (миграции).
- `asyncpg` (нужен wheel под 3.13 → 0.30.0), `greenlet` (async SQLAlchemy, на 3.13 сам не тянется).
- Redis для FSM (опц.; без него MemoryStorage). Docker Compose: db + redis + bot.
- Конфиг — pydantic-settings, значения только из `.env`.

## Архитектурные решения (не отступать без явного согласования)
- **Один бот**, не два. Тренер отделён фильтром `IsTrainer` (его `TRAINER_TG_ID` в конфиге);
  тренерский роутер гейтит всю свою ветку, остальные апдейты идут в клиентский.
- **Порт БД — в одном месте** (`DB_PORT` в `.env`). `database_url` собирается из частей
  в `config.py` (property). Внутри compose сервис `bot` переопределяет `DB_HOST=db`, `DB_PORT=5432`.
  Не возвращать `DATABASE_URL` строкой в `.env` — иначе рассинхрон портов.
- **Состояние диалогов — в FSM aiogram**, НЕ в колонке БД.
- **Фото — Telegram `file_id`** в БД, НЕ локальные пути.
- **Напоминания — в локальном времени клиента** (`clients.timezone`), не в серверном.
- **Планировщик — единый минутный тикер** (`services/scheduler.py`), НЕ цикл-на-юзера со sleep().
- **Все запросы через ORM/репозитории** (параметризация). Никаких f-string SQL.
- **Миграции только через Alembic.** Не делать `create_all`/ручной DDL на проде.
- Секреты только в `.env` (в `.gitignore` с первой секунды). В git не коммитить.

## Структура
```
bot/
  __main__.py          entrypoint (python -m bot)
  config.py            pydantic-settings; database_url собирается из частей
  db/ base, models, engine, repositories/ (base + clients)
  middlewares/db.py    сессия БД в каждый хендлер (data["session"])
  filters/is_trainer.py
  handlers/ client/{registration(готов), profile, program, checkin, payment}
            trainer/{review, clients, programs, broadcast}   # заглушки
  keyboards/  services/{scheduler, payments}  utils/logging.py
migrations/            alembic
```

## Локальный запуск
```
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env            # заполнить BOT_TOKEN, TRAINER_TG_ID; DB_PORT если 5432 занят
docker compose up -d db redis
alembic upgrade head            # или revision --autogenerate -m "..." при смене моделей
python -m bot
```
Проверка БД: `docker compose exec db psql -U fitbot -d fitbot -c "\dt"`

## Модель данных (Phase 0)
clients, programs, program_items, assignments, reminders, checkins, subscriptions, payments.
`checkins` — ядро продукта: напоминание → фото-отчёт → зачёт/не-зачёт тренером.

## Сделано
- Скелет (один бот, роли, middleware сессии, минутный тикер-заготовка, Docker, Alembic).
- Регистрация клиента: `/start` → имя → контакт (только свой, чужой из книги отсекается)
  → запись в БД → уведомление тренеру. Повторный `/start` не плодит дублей. FSM-флоу, проверен.

## Дальше (Phase 0), в порядке приоритета
1. **Программы**: тренер создаёт программу → назначает клиенту → клиент видит её. (следующий кусок)
2. Меню клиента (сейчас `TODO: показать меню клиента` в registration).
3. Напоминания (дописать логику тикера: локальное время + дни недели).
4. Отчёты (checkins): приём фото от клиента → очередь тренеру → зачёт/не-зачёт.
5. Платежи: YooKassa рекуррент + чек ФНС (перенос из проекта ConnectAssist).

## Уроки из «Жимова» (НЕ повторять)
- SQL-инъекции через f-string → только ORM/параметры.
- `.env` улетал в git → уже в `.gitignore`, проверять перед коммитом.
- Захардкоженный локальный путь для фото → только `file_id`.
- Состояние шага в колонке БД → FSM.
- Новое соединение на каждый запрос + цикл-на-юзера → пул + единый тикер.
