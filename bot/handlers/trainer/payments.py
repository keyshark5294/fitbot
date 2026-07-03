"""Тренерское подтверждение ручной оплаты. Кнопки приходят в заявке от клиента
(client/payment.py). Подтверждение продлевает подписку и уведомляет клиента.
Роутер под фильтром IsTrainer."""
import logging
from datetime import timezone
from zoneinfo import ZoneInfo

from aiogram import Bot, F, Router
from sqlalchemy.ext.asyncio import AsyncSession
from aiogram.types import CallbackQuery

from bot.db.repositories.clients import ClientRepository
from bot.db.repositories.subscriptions import SubscriptionRepository
from bot.services.payments import PLAN_AMOUNT, PLAN_NAME, PLAN_PERIOD_DAYS

logger = logging.getLogger(__name__)
router = Router()


@router.callback_query(F.data.startswith("payok:"))
async def payment_confirm(cb: CallbackQuery, session: AsyncSession, bot: Bot) -> None:
    client_id = int(cb.data.split(":", 1)[1])
    client = await ClientRepository(session).get(client_id)
    if client is None:
        await cb.answer("Клиент не найден", show_alert=True)
        return
    sub = await SubscriptionRepository(session).extend(
        client_id=client.id, plan=PLAN_NAME, amount=PLAN_AMOUNT, period_days=PLAN_PERIOD_DAYS
    )
    try:
        tz = ZoneInfo(client.timezone)
    except Exception:
        tz = timezone.utc
    end = sub.current_period_end.astimezone(tz).strftime("%d.%m.%Y")

    await cb.message.edit_reply_markup(reply_markup=None)
    await cb.answer("Оплата подтверждена ✅")
    await cb.message.answer(f"✅ Оплата {client.full_name or client.tg_id} подтверждена. Доступ до {end}.")
    try:
        await bot.send_message(
            client.tg_id, f"✅ Оплата подтверждена! Доступ активен до <b>{end}</b>. Спасибо 💪"
        )
    except Exception:
        logger.exception("Не удалось уведомить клиента id=%s о подтверждении оплаты", client.id)


@router.callback_query(F.data.startswith("payno:"))
async def payment_reject(cb: CallbackQuery, session: AsyncSession, bot: Bot) -> None:
    client_id = int(cb.data.split(":", 1)[1])
    client = await ClientRepository(session).get(client_id)
    if client is None:
        await cb.answer("Клиент не найден", show_alert=True)
        return
    await cb.message.edit_reply_markup(reply_markup=None)
    await cb.answer("Отклонено")
    await cb.message.answer(f"❌ Заявка {client.full_name or client.tg_id} отклонена.")
    try:
        await bot.send_message(
            client.tg_id,
            "❌ Оплата не подтверждена. Проверь перевод или свяжись с тренером.",
        )
    except Exception:
        logger.exception("Не удалось уведомить клиента id=%s об отклонении оплаты", client.id)
