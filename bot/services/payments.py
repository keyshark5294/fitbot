"""Платежи — РУЧНОЙ сценарий: клиент выбирает тариф, переводит на карту,
тренер подтверждает. Никакой YooKassa/вебхуков/чеков ФНС (решение под «одного тренера»).

Тарифы — константы ниже (поменять цену/название = поправить здесь)."""
from collections import namedtuple
from decimal import Decimal

from bot.config import settings

Plan = namedtuple("Plan", ["name", "amount"])

# ключ → тариф. Ключ уходит в callback_data, поэтому короткий и ascii.
PLANS: dict[str, Plan] = {
    "full": Plan("Питание + Тренировки", Decimal("15000")),
    "training": Plan("Тренировки", Decimal("10000")),
    "nutrition": Plan("Питание", Decimal("7000")),
}
PLAN_PERIOD_DAYS = 30
# за сколько дней до конца периода начинаем напоминать об оплате
EXPIRY_NOTICE_DAYS = 3


def format_amount(amount: Decimal | int) -> str:
    """15000 -> «15 000 ₽»."""
    return f"{int(amount):,}".replace(",", " ") + " ₽"


def _requisites() -> str:
    return (
        "<b>Как оплатить:</b>\n"
        f"Перевод на карту: <code>{settings.payment_card}</code>\n"
        f"Получатель: {settings.payment_recipient}\n\n"
        "После перевода нажми «✅ Я оплатил» — тренер подтвердит, и доступ продлится."
    )


def plans_overview() -> str:
    """Список всех тарифов (для выбора клиентом)."""
    lines = ["💳 <b>Тарифы онлайн-ведения</b> (за месяц):", ""]
    for plan in PLANS.values():
        lines.append(f"• <b>{plan.name}</b> — {format_amount(plan.amount)}")
    lines.append("")
    lines.append("Выбери тариф кнопкой ниже 👇")
    return "\n".join(lines)


def plan_payment_info(key: str) -> str:
    """Детали выбранного тарифа + реквизиты."""
    plan = PLANS[key]
    return (
        f"💳 <b>Тариф «{plan.name}»</b>\n"
        f"Стоимость: <b>{format_amount(plan.amount)}</b> / {PLAN_PERIOD_DAYS} дней\n\n"
        + _requisites()
    )
