"""Одна централизованная настройка логов (в Жимове был copy-paste в каждом файле)."""
import logging


def setup_logging(level: int = logging.INFO) -> None:
    logging.basicConfig(
        level=level,
        format="%(levelname)s | %(asctime)s | %(name)s | %(message)s",
    )
