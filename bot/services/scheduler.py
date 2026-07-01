"""Единый планировщик напоминаний: раз в минуту выбирает «созревшие» напоминания
и рассылает их. НИКАКИХ циклов-на-юзера со sleep() (антипаттерн Жимова)."""
import asyncio
import logging

from aiogram import Bot

from bot.db.engine import session_factory

logger = logging.getLogger(__name__)


async def reminder_ticker(bot: Bot, poll_seconds: int = 60) -> None:
    logger.info("Reminder ticker started (poll=%ss)", poll_seconds)
    while True:
        try:
            async with session_factory() as session:
                # TODO (интересная часть — тебе):
                #   1. взять «сейчас» и для каждого активного reminder перевести
                #      time_local в его client.timezone (zoneinfo);
                #   2. отобрать те, где локальное HH:MM == текущему и сегодняшний
                #      ISO-день недели входит в days_of_week;
                #   3. отправить сообщение и записать факт (например, checkin pending
                #      или отдельный лог отправки), чтобы не слать дубли в ту же минуту.
                _ = session  # заглушка, пока логики нет
        except Exception:
            logger.exception("reminder_ticker iteration failed")
        await asyncio.sleep(poll_seconds)
