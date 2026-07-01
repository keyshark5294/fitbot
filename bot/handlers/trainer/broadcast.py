"""Тренерская рассылка: сообщение всем активным клиентам.
/broadcast → текст → подтверждение → отправка с подсчётом доставлено/ошибок.
Шлём последовательно с микропаузой, чтобы не упереться в лимиты Telegram."""
import asyncio
import logging

from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.repositories.clients import ClientRepository

logger = logging.getLogger(__name__)
router = Router()


class Broadcast(StatesGroup):
    text = State()
    confirm = State()


def _confirm_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Отправить", callback_data="bcast:send"),
        InlineKeyboardButton(text="✖️ Отмена", callback_data="bcast:cancel"),
    ]])


@router.message(Command("broadcast"))
async def broadcast_start(message: Message, state: FSMContext) -> None:
    await state.set_state(Broadcast.text)
    await message.answer("Текст рассылки? Пришли сообщение (или /cancel для отмены).")


@router.message(Broadcast.text, Command("cancel"))
async def broadcast_cancel_input(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Рассылка отменена.")


@router.message(Broadcast.text, F.text)
async def broadcast_preview(message: Message, session: AsyncSession, state: FSMContext) -> None:
    active = [c for c in await ClientRepository(session).list_all() if c.status == "active"]
    if not active:
        await state.clear()
        await message.answer("Нет активных клиентов для рассылки.")
        return
    await state.update_data(text=message.html_text)
    await state.set_state(Broadcast.confirm)
    await message.answer(
        f"Отправить это сообщение <b>{len(active)}</b> клиентам?\n\n{message.html_text}",
        reply_markup=_confirm_kb(),
    )


@router.callback_query(Broadcast.confirm, F.data == "bcast:cancel")
async def broadcast_cancel(cb: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await cb.message.edit_reply_markup(reply_markup=None)
    await cb.message.answer("Рассылка отменена.")
    await cb.answer()


@router.callback_query(Broadcast.confirm, F.data == "bcast:send")
async def broadcast_send(
    cb: CallbackQuery, session: AsyncSession, state: FSMContext, bot: Bot
) -> None:
    data = await state.get_data()
    await state.clear()
    text = data["text"]
    await cb.message.edit_reply_markup(reply_markup=None)
    await cb.answer("Отправляю…")

    active = [c for c in await ClientRepository(session).list_all() if c.status == "active"]
    sent, failed = 0, 0
    for client in active:
        try:
            await bot.send_message(client.tg_id, text)
            sent += 1
        except Exception:
            failed += 1
            logger.warning("Рассылка: не доставлено клиенту id=%s", client.id)
        await asyncio.sleep(0.05)

    await cb.message.answer(f"Готово. Доставлено: {sent}, ошибок: {failed}.")
