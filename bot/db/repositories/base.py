"""Базовый репозиторий. Наследники инкапсулируют запросы к конкретной таблице,
хендлеры не пишут SQL напрямую."""
from sqlalchemy.ext.asyncio import AsyncSession


class BaseRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
