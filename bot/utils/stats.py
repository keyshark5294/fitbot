"""Мелкие вычисления для статистики профиля. Всё завязано на ЛОКАЛЬНОЕ время
клиента (clients.timezone), не на серверное — как и напоминания (урок Жимова)."""
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo


def _tz(tz_name: str) -> ZoneInfo:
    try:
        return ZoneInfo(tz_name)
    except Exception:
        return ZoneInfo("UTC")


def plural_ru(n: int, one: str, few: str, many: str) -> str:
    """Русское склонение по числу: 1 день / 2 дня / 5 дней."""
    n = abs(n) % 100
    if 11 <= n <= 14:
        return many
    n1 = n % 10
    if n1 == 1:
        return one
    if 2 <= n1 <= 4:
        return few
    return many


def days_since(created_at: datetime, tz_name: str) -> int:
    """Сколько локальных суток прошло с регистрации (сегодня = 0)."""
    tz = _tz(tz_name)
    start = created_at.astimezone(tz).date()
    today = datetime.now(tz).date()
    return (today - start).days


def current_streak(
    approved_at: list[datetime], tz_name: str, today: date | None = None
) -> int:
    """Серия — подряд идущие локальные дни с зачтённым отчётом, оканчивающиеся
    сегодня или вчера (вчера — чтобы серия не «сгорала» до конца текущего дня)."""
    tz = _tz(tz_name)
    local_days = {dt.astimezone(tz).date() for dt in approved_at}
    if not local_days:
        return 0
    today = today or datetime.now(tz).date()
    if today in local_days:
        cursor = today
    elif (today - timedelta(days=1)) in local_days:
        cursor = today - timedelta(days=1)
    else:
        return 0
    streak = 0
    while cursor in local_days:
        streak += 1
        cursor -= timedelta(days=1)
    return streak
