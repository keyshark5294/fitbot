"""Форматирование доменных объектов в текст для Telegram (HTML parse_mode)."""
from html import escape

from bot.db.models import Program, Reminder

KIND_LABELS: dict[str, str] = {
    "training": "🏋️ Тренировки",
    "nutrition": "🥗 Питание",
    "combined": "🔁 Комбо",
}

# Виды отчёта клиента (checkins.kind)
CHECKIN_KIND_LABELS: dict[str, str] = {
    "workout": "🏋️ Тренировка",
    "meal": "🥗 Питание",
    "progress": "📈 Прогресс",
}


def format_program(program: Program) -> str:
    """Карточка программы. Пункты (program_items) добавим позже."""
    kind = KIND_LABELS.get(program.kind, program.kind)
    lines = [f"<b>{escape(program.title)}</b>", kind]
    if program.description:
        lines.append("")
        lines.append(escape(program.description))
    return "\n".join(lines)


# Виды напоминаний (reminders.kind) — совпадают с checkins по meal/workout
REMINDER_KIND_LABELS: dict[str, str] = {
    "workout": "🏋️ Тренировка",
    "meal": "🥗 Питание",
}

DAY_SHORT: dict[int, str] = {1: "Пн", 2: "Вт", 3: "Ср", 4: "Чт", 5: "Пт", 6: "Сб", 7: "Вс"}


def days_summary(days: list[int]) -> str:
    s = set(days)
    if s == {1, 2, 3, 4, 5, 6, 7}:
        return "ежедневно"
    if s == {1, 2, 3, 4, 5}:
        return "по будням"
    if s == {6, 7}:
        return "выходные"
    return " ".join(DAY_SHORT[d] for d in sorted(s) if d in DAY_SHORT)


def format_reminder(rem: Reminder) -> str:
    kind = REMINDER_KIND_LABELS.get(rem.kind, rem.kind)
    return (
        f"{kind} «{escape(rem.label)}» в {rem.time_local.strftime('%H:%M')} "
        f"({days_summary(rem.days_of_week)})"
    )
