"""Клиентский модуль «Профиль»: данные клиента + статистика.
Вход по команде /profile и по кнопке меню «👤 Профиль»."""
from html import escape

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.repositories.checkins import CheckinRepository
from bot.db.repositories.clients import ClientRepository
from bot.db.repositories.programs import ProgramRepository
from bot.keyboards import BTN_PROFILE
from bot.utils.stats import current_streak, days_since, plural_ru

router = Router()

STATUS_LABELS: dict[str, str] = {
    "active": "активен",
    "paused": "на паузе",
    "stopped": "остановлен",
}


@router.message(Command("profile"))
@router.message(F.text == BTN_PROFILE)
async def my_profile(message: Message, session: AsyncSession) -> None:
    client = await ClientRepository(session).get_by_tg_id(message.from_user.id)
    if client is None:
        await message.answer("Сначала пройди регистрацию — отправь /start.")
        return

    program = await ProgramRepository(session).get_active_for_client(client.id)
    checkins = CheckinRepository(session)
    counts = await checkins.status_counts(client.id)

    lines = [
        "<b>👤 Твой профиль</b>",
        f"Имя: {escape(client.full_name) if client.full_name else '—'}",
        f"Телефон: {escape(client.phone) if client.phone else '—'}",
        f"Часовой пояс: {escape(client.timezone)}",
        f"Статус: {STATUS_LABELS.get(client.status, client.status)}",
        "",
        f"📋 Программа: {escape(program.title) if program else 'не назначена'}",
    ]

    days = days_since(client.created_at, client.timezone)
    if days == 0:
        lines.append("📅 С нами: сегодня первый день")
    else:
        lines.append(f"📅 С нами: {days} {plural_ru(days, 'день', 'дня', 'дней')}")

    total = sum(counts.values())
    if total == 0:
        lines.append("📸 Отчёты появятся здесь, как только заработает эта функция.")
    else:
        approved = counts.get("approved", 0)
        pending = counts.get("pending", 0)
        lines.append(f"✅ Зачтено отчётов: {approved}   ⏳ На проверке: {pending}")
        streak = current_streak(
            await checkins.approved_created_at(client.id), client.timezone
        )
        if streak:
            lines.append(f"🔥 Серия: {streak} {plural_ru(streak, 'день', 'дня', 'дней')} подряд")

    await message.answer("\n".join(lines))
