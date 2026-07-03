"""Единый планировщик: раз в минуту рассылает «созревшие» напоминания и раз в день
(в 12:00 локального времени клиента) — уведомления об истечении подписки.
НИКАКИХ циклов-на-юзера со sleep() (антипаттерн Жимова).

Всё считаем в ЛОКАЛЬНОМ времени клиента (clients.timezone). Дедуп в пределах
минуты — in-memory set (один процесс, один тикер)."""
import asyncio
import logging
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from aiogram import Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot.db.engine import session_factory
from bot.db.repositories.reminders import ReminderRepository
from bot.db.repositories.subscriptions import SubscriptionRepository
from bot.services.payments import EXPIRY_NOTICE_DAYS
from bot.utils.stats import plural_ru

logger = logging.getLogger(__name__)


def _client_tz(tz_name: str) -> ZoneInfo | timezone:
    try:
        return ZoneInfo(tz_name)
    except Exception:
        return timezone.utc


def _reminder_kb(kind: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="📸 Отправить отчёт", callback_data=f"remck:{kind}")
    ]])


async def _process_reminders(bot: Bot, now_utc: datetime, sent: set) -> None:
    async with session_factory() as session:
        pairs = await ReminderRepository(session).list_active_with_client()
    for reminder, client in pairs:
        local = now_utc.astimezone(_client_tz(client.timezone))
        if local.isoweekday() not in reminder.days_of_week:
            continue
        if (local.hour, local.minute) != (reminder.time_local.hour, reminder.time_local.minute):
            continue
        key = ("rem", reminder.id, local.date().isoformat())
        if key in sent:
            continue
        sent.add(key)
        try:
            await bot.send_message(
                client.tg_id,
                f"⏰ Напоминание: <b>{reminder.label}</b>\nПора отправить отчёт!",
                reply_markup=_reminder_kb(reminder.kind),
            )
        except Exception:
            logger.exception(
                "Напоминание id=%s клиенту id=%s не доставлено", reminder.id, client.id
            )


async def _process_subscriptions(bot: Bot, now_utc: datetime, sent: set) -> None:
    """Раз в день в 12:00 локального: напомнить об истечении / отметить past_due."""
    async with session_factory() as session:
        subs = SubscriptionRepository(session)
        pairs = await subs.list_active_with_client()
        for sub, client in pairs:
            local = now_utc.astimezone(_client_tz(client.timezone))
            if (local.hour, local.minute) != (12, 0):
                continue
            key = ("subexp", sub.id, local.date().isoformat())
            if key in sent:
                continue
            days_left = (sub.current_period_end.astimezone(local.tzinfo).date() - local.date()).days
            if days_left <= 0:
                sent.add(key)
                await subs.set_status(sub.id, "past_due")
                text = "⚠️ Подписка истекла. Продли через «💳 Оплата», чтобы продолжить."
            elif 0 < days_left <= EXPIRY_NOTICE_DAYS:
                sent.add(key)
                text = (
                    f"⏳ Подписка заканчивается через {days_left} "
                    f"{plural_ru(days_left, 'день', 'дня', 'дней')}. "
                    "Продли через «💳 Оплата»."
                )
            else:
                continue
            try:
                await bot.send_message(client.tg_id, text)
            except Exception:
                logger.exception(
                    "Уведомление о подписке sub=%s клиенту id=%s не доставлено", sub.id, client.id
                )


async def reminder_ticker(bot: Bot, poll_seconds: int = 60) -> None:
    logger.info("Ticker started (poll=%ss)", poll_seconds)
    sent: set = set()
    last_minute: str | None = None

    while True:
        try:
            now_utc = datetime.now(timezone.utc)
            minute_key = now_utc.strftime("%Y%m%d%H%M")
            if minute_key != last_minute:
                sent.clear()  # новая минута — старые ключи не нужны
                last_minute = minute_key
            await _process_reminders(bot, now_utc, sent)
            await _process_subscriptions(bot, now_utc, sent)
        except Exception:
            logger.exception("ticker iteration failed")
        await asyncio.sleep(poll_seconds)
