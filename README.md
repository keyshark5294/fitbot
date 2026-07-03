# Fitbot — онлайн-сопровождение тренировок

Телеграм-бот для одного тренера и его клиентов: персональные программы, напоминания,
фото-отчёты с проверкой тренером и ручная оплата. Один бот, роли разведены фильтром
(`TRAINER_TG_ID` — тренер, `ADMIN_TG_ID` — владелец с таким же доступом).

- aiogram 3 (long-polling) · PostgreSQL 16 + SQLAlchemy 2.0 (async) + Alembic
- Redis для FSM (опц.; без него — MemoryStorage)
- Напоминания и уведомления об оплате — единый минутный тикер ([bot/services/scheduler.py](bot/services/scheduler.py))
- Фото хранятся как Telegram `file_id`, не файлами

## Роли

| Роль | Кто | Доступ |
|------|-----|--------|
| Клиент | все остальные | своё меню: программа, отчёты, профиль, оплата |
| Тренер | `TRAINER_TG_ID` | тренерские команды **+ все уведомления** |
| Админ | `ADMIN_TG_ID` (опц.) | тот же доступ, что у тренера; уведомления идут только тренеру |

---

## Инструкция по использованию

### Клиент

1. **`/start`** → регистрация: ввести имя → нажать кнопку «📱 Поделиться контактом»
   (принимается только свой номер). Повторный `/start` не создаёт дубль.
2. Появляется меню:
   - **📋 Моя программа** — назначенная тренером программа.
   - **📸 Отчёт** — отправить фото-отчёт: выбрать вид (тренировка/питание/прогресс) →
     прислать фото → комментарий (или `/skip`). Уходит тренеру на проверку.
   - **👤 Профиль** — данные, активная программа, «с нами N дней», зачтённые отчёты, серия.
   - **💳 Оплата** — тариф и реквизиты; после перевода нажать «✅ Я оплатил» →
     тренер подтвердит → срок продлится.
3. **Напоминания** приходят по расписанию с кнопкой «📸 Отправить отчёт» — сразу в отчёт.
4. О скором окончании подписки бот предупреждает за 3 дня.

### Тренер / Админ

- **`/clients`** — список клиентов → карточка (контакт, статус, программа, оплата, статистика).
  Из карточки: «📋 Назначить программу», «⏰ Напоминания» (создать/удалить: тип, время, дни).
- **`/programs`** — список программ, создание (название → описание → вид) и назначение клиенту.
- **`/reports`** — очередь отчётов на проверку. По каждому: «✅ Зачёт» / «❌ Не зачёт»
  (с указанием причины). Клиенту приходит результат.
- **`/broadcast`** — рассылка сообщения всем активным клиентам (с превью и подтверждением).
- **Уведомления** (только тренеру): новый клиент, новый отчёт, заявка на оплату.
  Заявку на оплату подтверждают кнопкой «✅ Подтвердить» — подписка продлевается.

---

## Настройка `.env`

Файл `.env` в git не хранится — создать вручную в корне проекта:

```dotenv
# Telegram
BOT_TOKEN=<токен от @BotFather>
TRAINER_TG_ID=<telegram id тренера>
ADMIN_TG_ID=<telegram id владельца>      # опционально

# PostgreSQL
POSTGRES_USER=fitbot
POSTGRES_PASSWORD=<надёжный пароль>
POSTGRES_DB=fitbot
DB_PORT=5432                              # 5433, если 5432 занят локально
REDIS_PORT=6379

# Собирается из частей выше; хост localhost — для запуска с машины.
# Внутри docker compose сервис bot сам подменит host на db/redis.
DATABASE_URL=postgresql+asyncpg://fitbot:<тот же пароль>@localhost:5432/fitbot
REDIS_URL=redis://localhost:6379/0

# Оплата (ручной сценарий)
PAYMENT_CARD=0000 0000 0000 0000
PAYMENT_RECIPIENT=Имя Получателя
```

Свой telegram id можно узнать у `@userinfobot`.

---

## Локальный запуск

Нужен Python 3.12+ (проверено на 3.12 и 3.13).

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# создать .env (см. выше)

docker compose up -d db redis     # поднять базу и redis
alembic upgrade head              # применить миграции (уже описаны)
python -m bot                     # запустить бота
```

Проверка БД: `docker compose exec db psql -U fitbot -d fitbot -c "\dt"`

Если `port is already allocated` на 5432/6379 — порт занят. Поставь свободный
(`DB_PORT=5433`) и синхронно поправь порт в `DATABASE_URL`.

---

## Деплой на сервер (Docker Compose)

Бот на long-polling — входящие порты/домен не нужны. На чистом VPS (Ubuntu/Debian):

```bash
curl -fsSL https://get.docker.com | sh          # Docker + Compose
git clone https://github.com/keyshark5294/fitbot.git && cd fitbot
# создать .env с боевыми значениями (надёжный POSTGRES_PASSWORD, реальные реквизиты)
docker compose up -d --build
docker compose logs -f bot                       # ждём: alembic upgrade head → Start polling
```

Контейнер `bot` при старте сам прогоняет `alembic upgrade head` (см.
[docker-entrypoint.sh](docker-entrypoint.sh)) — на чистой базе таблицы создаются автоматически.
Порты БД/Redis забинжены на `127.0.0.1` (наружу не торчат).

**Обновление:** `git pull && docker compose up -d --build`.

> ⚠️ Один polling на токен: пока сервер работает, локальный `python -m bot`
> запускать нельзя (иначе `Conflict: terminated by other getUpdates`).

---

## Настройка в @BotFather

- **Commands** (`/setcommands`): `start`, `program`, `profile` — клиентские;
  `clients`, `programs`, `reports`, `broadcast` — тренерские (закрыты фильтром, у клиента не сработают).
- **About / Description** — короткое описание бота для профиля и стартового экрана.

---

## Структура

```
bot/
  __main__.py            entrypoint (python -m bot) + запуск тикера
  config.py              настройки из .env (pydantic-settings)
  db/
    models.py            ORM-модели (SQLAlchemy 2.0)
    engine.py            async-движок + пул
    repositories/        запросы к БД (clients, programs, checkins, reminders, subscriptions)
  middlewares/db.py      сессия БД в каждый хендлер (data["session"])
  filters/is_trainer.py  роль тренер/админ
  handlers/
    client/  registration profile program checkin payment
    trainer/ clients programs reminders review payments broadcast
  services/
    scheduler.py         минутный тикер: напоминания + уведомления об оплате
    payments.py          тариф «Сопровождение» + сборка реквизитов (ручная оплата)
  utils/  format.py stats.py logging.py
migrations/              alembic
```

Архитектурные принципы и история решений — в [CLAUDE.md](CLAUDE.md).
