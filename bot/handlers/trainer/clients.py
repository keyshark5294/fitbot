"""Тренерский модуль «Клиенты»: список клиентов и карточка (кто, программа,
статус, статистика). Отсюда же можно назначить программу конкретному клиенту
(обратное направление к trainer/programs, где сначала выбирают программу).
Роутер под фильтром IsTrainer — роль не проверяем."""
import logging
from html import escape

from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.models import Client
from bot.db.repositories.checkins import CheckinRepository
from bot.db.repositories.clients import ClientRepository
from bot.db.repositories.programs import ProgramRepository
from bot.utils.format import format_program
from bot.utils.stats import days_since, plural_ru

logger = logging.getLogger(__name__)
router = Router()

STATUS_LABELS: dict[str, str] = {
    "active": "🟢 активен",
    "paused": "🟡 на паузе",
    "stopped": "🔴 остановлен",
}


def _clients_kb(clients: list[Client]) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(
            text=c.full_name or f"id{c.tg_id}",
            callback_data=f"tclient:{c.id}",
        )]
        for c in clients
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


async def _render_card(session: AsyncSession, client: Client) -> str:
    program = await ProgramRepository(session).get_active_for_client(client.id)
    counts = await CheckinRepository(session).status_counts(client.id)

    username = f" (@{escape(client.tg_username)})" if client.tg_username else ""
    days = days_since(client.created_at, client.timezone)
    days_str = "сегодня первый день" if days == 0 else (
        f"{days} {plural_ru(days, 'день', 'дня', 'дней')}"
    )
    lines = [
        f"<b>{escape(client.full_name) if client.full_name else 'Без имени'}</b>{username}",
        f"Телефон: {escape(client.phone) if client.phone else '—'}",
        f"Статус: {STATUS_LABELS.get(client.status, client.status)}",
        f"Часовой пояс: {escape(client.timezone)}",
        f"С нами: {days_str}",
        f"📋 Программа: {escape(program.title) if program else 'не назначена'}",
    ]
    total = sum(counts.values())
    if total:
        lines.append(
            f"📸 Отчёты — зачтено: {counts.get('approved', 0)}, "
            f"на проверке: {counts.get('pending', 0)}, "
            f"не зачтено: {counts.get('rejected', 0)}"
        )
    return "\n".join(lines)


@router.message(Command("clients"))
async def clients_list(message: Message, session: AsyncSession) -> None:
    clients = await ClientRepository(session).list_all()
    if not clients:
        await message.answer("Клиентов пока нет.")
        return
    await message.answer(
        f"<b>Клиенты</b> ({len(clients)}):",
        reply_markup=_clients_kb(clients),
    )


@router.callback_query(F.data.startswith("tclient:"))
async def client_card(cb: CallbackQuery, session: AsyncSession) -> None:
    client_id = int(cb.data.split(":", 1)[1])
    client = await ClientRepository(session).get(client_id)
    if client is None:
        await cb.answer("Клиент не найден", show_alert=True)
        return
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text="📋 Назначить программу", callback_data=f"cassign_pick:{client.id}"
        )
    ]])
    await cb.message.answer(await _render_card(session, client), reply_markup=kb)
    await cb.answer()


# ---------- назначение программы от клиента ----------

@router.callback_query(F.data.startswith("cassign_pick:"))
async def assign_pick_program(cb: CallbackQuery, session: AsyncSession) -> None:
    client_id = int(cb.data.split(":", 1)[1])
    programs = await ProgramRepository(session).list_active()
    if not programs:
        await cb.answer("Сначала создай программу: /programs", show_alert=True)
        return
    rows = [
        [InlineKeyboardButton(text=p.title, callback_data=f"cassign:{client_id}:{p.id}")]
        for p in programs
    ]
    await cb.message.answer(
        "Какую программу назначить?",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
    )
    await cb.answer()


@router.callback_query(F.data.startswith("cassign:"))
async def assign_do(cb: CallbackQuery, session: AsyncSession, bot: Bot) -> None:
    _, client_id_s, program_id_s = cb.data.split(":")
    client_id, program_id = int(client_id_s), int(program_id_s)

    programs = ProgramRepository(session)
    program = await programs.get(program_id)
    client = await ClientRepository(session).get(client_id)
    if program is None or client is None:
        await cb.answer("Программа или клиент не найдены", show_alert=True)
        return

    await programs.assign(client_id=client.id, program_id=program.id)
    await cb.message.edit_reply_markup(reply_markup=None)
    await cb.message.answer(
        f"✅ «{program.title}» назначена клиенту {client.full_name or client.tg_id}."
    )
    await cb.answer()

    try:
        await bot.send_message(
            client.tg_id,
            "🎯 Тренер назначил тебе программу:\n\n" + format_program(program),
        )
    except Exception:
        logger.exception("Не удалось уведомить клиента id=%s о назначении", client.id)
