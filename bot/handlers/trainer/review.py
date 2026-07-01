"""Тренерская проверка отчётов: зачёт/не-зачёт (с причиной) + очередь /reports.
Кнопки приходят вместе с фото-отчётом (см. client/checkin.py)."""
import logging
from html import escape

from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.repositories.checkins import CheckinRepository
from bot.db.repositories.clients import ClientRepository
from bot.utils.format import CHECKIN_KIND_LABELS

logger = logging.getLogger(__name__)
router = Router()

SKIP_TOKENS = {"/skip", "-", "нет"}


class RejectReason(StatesGroup):
    waiting = State()


async def _notify_client(bot: Bot, session: AsyncSession, checkin, reason: str | None) -> None:
    client = await ClientRepository(session).get(checkin.client_id)
    if client is None:
        return
    kind = CHECKIN_KIND_LABELS.get(checkin.kind, checkin.kind)
    if checkin.status == "approved":
        text = f"✅ Твой отчёт «{kind}» зачтён! Так держать 💪"
    else:
        text = f"❌ Отчёт «{kind}» не зачтён."
        if reason:
            text += f"\nПричина: {escape(reason)}"
    try:
        await bot.send_message(client.tg_id, text)
    except Exception:
        logger.exception("Не удалось уведомить клиента id=%s о проверке", client.id)


@router.callback_query(F.data.startswith("ckok:"))
async def approve(cb: CallbackQuery, session: AsyncSession, bot: Bot) -> None:
    checkin_id = int(cb.data.split(":", 1)[1])
    checkin = await CheckinRepository(session).set_status(checkin_id, "approved")
    if checkin is None:
        await cb.answer("Отчёт не найден", show_alert=True)
        return
    await cb.message.edit_reply_markup(reply_markup=None)
    await cb.answer("Зачтено ✅")
    await _notify_client(bot, session, checkin, None)


@router.callback_query(F.data.startswith("ckno:"))
async def reject_ask_reason(cb: CallbackQuery, state: FSMContext) -> None:
    checkin_id = int(cb.data.split(":", 1)[1])
    await state.set_state(RejectReason.waiting)
    await state.update_data(checkin_id=checkin_id)
    await cb.message.edit_reply_markup(reply_markup=None)
    await cb.message.answer("Причина «не зачёт»? Напиши текст или /skip.")
    await cb.answer()


async def _apply_reject(
    message: Message, session: AsyncSession, state: FSMContext, bot: Bot, reason: str | None
) -> None:
    data = await state.get_data()
    await state.clear()
    checkin = await CheckinRepository(session).set_status(
        data["checkin_id"], "rejected", trainer_comment=reason
    )
    if checkin is None:
        await message.answer("Отчёт не найден.")
        return
    await message.answer("Отмечено «не зачёт» ❌")
    await _notify_client(bot, session, checkin, reason)


@router.message(RejectReason.waiting, F.text.in_(SKIP_TOKENS))
async def reject_skip(
    message: Message, session: AsyncSession, state: FSMContext, bot: Bot
) -> None:
    await _apply_reject(message, session, state, bot, None)


@router.message(RejectReason.waiting, F.text.startswith("/"))
async def reject_cancel_by_command(message: Message, state: FSMContext) -> None:
    # команда вместо причины — не считаем её причиной, отменяем ввод
    await state.clear()
    await message.answer("Ввод причины отменён. Повтори команду.")


@router.message(RejectReason.waiting, F.text)
async def reject_apply(
    message: Message, session: AsyncSession, state: FSMContext, bot: Bot
) -> None:
    await _apply_reject(message, session, state, bot, message.text.strip())


# ---------- очередь /reports ----------

@router.message(Command("reports"))
async def reports_queue(message: Message, session: AsyncSession) -> None:
    pending = await CheckinRepository(session).list_pending()
    if not pending:
        await message.answer("Очередь пуста — все отчёты проверены 👍")
        return
    clients = ClientRepository(session)
    rows = []
    for ch in pending:
        client = await clients.get(ch.client_id)
        name = (client.full_name if client and client.full_name else f"id{ch.client_id}")
        kind = CHECKIN_KIND_LABELS.get(ch.kind, ch.kind)
        rows.append([InlineKeyboardButton(
            text=f"{name} — {kind}", callback_data=f"rev:{ch.id}"
        )])
    await message.answer(
        f"На проверке: {len(pending)}",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
    )


@router.callback_query(F.data.startswith("rev:"))
async def review_open(cb: CallbackQuery, session: AsyncSession, bot: Bot) -> None:
    checkin_id = int(cb.data.split(":", 1)[1])
    checkin = await CheckinRepository(session).get(checkin_id)
    if checkin is None or checkin.status != "pending":
        await cb.answer("Уже проверен или не найден", show_alert=True)
        return
    client = await ClientRepository(session).get(checkin.client_id)
    kind = CHECKIN_KIND_LABELS.get(checkin.kind, checkin.kind)
    caption = f"📥 Отчёт: <b>{escape(client.full_name or str(client.tg_id)) if client else '—'}</b>\n{kind}"
    if checkin.comment:
        caption += f"\n\n{escape(checkin.comment)}"
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Зачёт", callback_data=f"ckok:{checkin.id}"),
        InlineKeyboardButton(text="❌ Не зачёт", callback_data=f"ckno:{checkin.id}"),
    ]])
    if checkin.photo_file_id:
        await bot.send_photo(cb.from_user.id, checkin.photo_file_id, caption=caption, reply_markup=kb)
    else:
        await bot.send_message(cb.from_user.id, caption, reply_markup=kb)
    await cb.answer()
