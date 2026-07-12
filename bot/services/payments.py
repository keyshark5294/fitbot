"""Платежи — РУЧНОЙ сценарий: клиент переводит на карту, тренер подтверждает.
Никакой YooKassa/вебхуков/чеков ФНС (решение под «одного тренера»).
Тариф один — «Сопровождение», зашит константами (при желании поменять число тут)."""
from decimal import Decimal

from bot.config import settings

PLAN_NAME = "Сопровождение"
PLAN_AMOUNT: Decimal = Decimal("15000")
PLAN_PERIOD_DAYS = 30
# за сколько дней до конца периода начинаем напоминать об оплате
EXPIRY_NOTICE_DAYS = 3


def format_amount(amount: Decimal | int) -> str:
    """9900 -> «9 900 ₽»."""
    return f"{int(amount):,}".replace(",", " ") + " ₽"


def payment_info() -> str:
    """Текст с тарифом и реквизитами для клиента."""
    return (
        f"💳 <b>Тариф «{PLAN_NAME}»</b>\n"
        f"Стоимость: <b>{format_amount(PLAN_AMOUNT)}</b> / {PLAN_PERIOD_DAYS} дней\n\n"
        "Что входит: персональная программа, напоминания, безлимит фото-отчётов "
        "с разбором тренером, обратная связь.\n\n"
        "<b>Как оплатить:</b>\n"
        f"Перевод на карту: <code>{settings.payment_card}</code>\n"
        f"Получатель: {settings.payment_recipient}\n\n"
        "После перевода нажми «Я оплатил» — тренер подтвердит, и доступ продлится."
    )
