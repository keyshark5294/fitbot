"""Единый планировщик напоминаний: раз в минуту выбирает «созревшие» напоминания
и рассылает их. НИКАКИХ циклов-на-юзера со sleep() (антипаттерн Жимова).

Время напоминаний — ЛОКАЛЬНОЕ для клиента (reminders.time_local + clients.timezone);
тут переводим «сейчас» в таймзону клиента и сверяем HH:MM и день недели.
Дедуп в пределах минуты — по in-memory set (один процесс, один тикер)."""
import asyncio
import logging
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from aiogram import Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot.db.engine import session_factory
from bot.db.repositories.reminders import ReminderRepository

logger = logging.getLogger(__name__)


def _reminder_kb(kind: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="📸 Отправить отчёт", callback_data=f"remck:{kind}")
    ]])


async def reminder_ticker(bot: Bot, poll_seconds: int = 60) -> None:
    logger.info("Reminder ticker started (poll=%ss)", poll_seconds)
    sent: set[tuple[int, str]] = set()  # (reminder_id, local_date) уже отправленные
    last_minute: str | None = None

    while True:
        try:
            now_utc = datetime.now(timezone.utc)
            minute_key = now_utc.strftime("%Y%m%d%H%M")
            if minute_key != last_minute:
                sent.clear()  # новая минута — старые ключи не нужны
                last_minute = minute_key

            async with session_factory() as session:
                pairs = await ReminderRepository(session).list_active_with_client()

            for reminder, client in pairs:
                try:
                    tz = ZoneInfo(client.timezone)
                except Exception:
                    tz = timezone.utc
                local = now_utc.astimezone(tz)
                if local.isoweekday() not in reminder.days_of_week:
                    continue
                if (local.hour, local.minute) != (
                    reminder.time_local.hour,
                    reminder.time_local.minute,
                ):
                    continue
                key = (reminder.id, local.date().isoformat())
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
                        "Не удалось отправить напоминание id=%s клиенту id=%s",
                        reminder.id, client.id,
                    )
        except Exception:
            logger.exception("reminder_ticker iteration failed")
        await asyncio.sleep(poll_seconds)
