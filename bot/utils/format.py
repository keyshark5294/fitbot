"""Форматирование доменных объектов в текст для Telegram (HTML parse_mode)."""
from html import escape

from bot.db.models import Program

KIND_LABELS: dict[str, str] = {
    "training": "🏋️ Тренировки",
    "nutrition": "🥗 Питание",
    "combined": "🔁 Комбо",
}


def format_program(program: Program) -> str:
    """Карточка программы. Пункты (program_items) добавим позже."""
    kind = KIND_LABELS.get(program.kind, program.kind)
    lines = [f"<b>{escape(program.title)}</b>", kind]
    if program.description:
        lines.append("")
        lines.append(escape(program.description))
    return "\n".join(lines)
