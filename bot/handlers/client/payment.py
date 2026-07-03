"""Клиентский модуль «Оплата» (ручной сценарий): показать тариф+реквизиты,
кнопка «Я оплатил» → заявка тренеру на подтверждение.
Вход по кнопке меню «💳 Оплата» и команде /pay."""
import logging
from datetime import datetime, timezone
from html import escape
from zoneinfo import ZoneInfo

from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config import settings
from bot.db.repositories.clients import ClientRepository
from bot.db.repositories.subscriptions import SubscriptionRepository
from bot.keyboards import BTN_PAY
from bot.services.payments import PLAN_AMOUNT, PLAN_NAME, format_amount, payment_info

logger = logging.getLogger(__name__)
router = Router()


def _status_line(sub, tz_name: str) -> str:
    if sub is None:
        return "Активной подписки нет."
    now = datetime.now(timezone.utc)
    try:
        tz = ZoneInfo(tz_name)
    except Exception:
        tz = timezone.utc
    end = sub.current_period_end.astimezone(tz).strftime("%d.%m.%Y")
    if sub.status == "active" and sub.current_period_end > now:
        return f"✅ Оплачено до <b>{end}</b>."
    return f"⚠️ Подписка неактивна (истекла {end})."


@router.message(Command("pay"))
@router.message(F.text == BTN_PAY)
async def pay(message: Message, session: AsyncSession) -> None:
    client = await ClientRepository(session).get_by_tg_id(message.from_user.id)
    if client is None:
        await message.answer("Сначала пройди регистрацию — отправь /start.")
        return
    sub = await SubscriptionRepository(session).get_current(client.id)
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Я оплатил", callback_data="pay:claim")
    ]])
    await message.answer(
        _status_line(sub, client.timezone) + "\n\n" + payment_info(),
        reply_markup=kb,
    )


@router.callback_query(F.data == "pay:claim")
async def pay_claim(cb: CallbackQuery, session: AsyncSession, bot: Bot) -> None:
    client = await ClientRepository(session).get_by_tg_id(cb.from_user.id)
    if client is None:
        await cb.answer("Сначала пройди регистрацию", show_alert=True)
        return
    await cb.message.edit_reply_markup(reply_markup=None)
    await cb.message.answer("Заявка отправлена тренеру. Как подтвердит — доступ продлится ✅")
    await cb.answer()

    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"payok:{client.id}"),
        InlineKeyboardButton(text="❌ Отклонить", callback_data=f"payno:{client.id}"),
    ]])
    username = f" (@{escape(client.tg_username)})" if client.tg_username else ""
    try:
        await bot.send_message(
            settings.trainer_tg_id,
            f"💰 Заявка на оплату: <b>{escape(client.full_name or str(client.tg_id))}</b>{username}\n"
            f"Тариф «{PLAN_NAME}» — {format_amount(PLAN_AMOUNT)}",
            reply_markup=kb,
        )
    except Exception:
        logger.exception("Не удалось отправить заявку на оплату тренеру, клиент id=%s", client.id)
