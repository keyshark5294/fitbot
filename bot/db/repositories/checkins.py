"""Репозиторий отчётов (checkins). Пока используется только для статистики
в профиле; приём фото и очередь тренеру — отдельная задача (пункт 7)."""
from datetime import datetime

from sqlalchemy import func, select

from bot.db.models import Checkin
from bot.db.repositories.base import BaseRepository


class CheckinRepository(BaseRepository):
    async def status_counts(self, client_id: int) -> dict[str, int]:
        """{'approved': N, 'pending': M, ...} по клиенту. Пустой dict — нет отчётов."""
        result = await self.session.execute(
            select(Checkin.status, func.count())
            .where(Checkin.client_id == client_id)
            .group_by(Checkin.status)
        )
        return {status: count for status, count in result.all()}

    async def approved_created_at(self, client_id: int) -> list[datetime]:
        """Моменты зачтённых отчётов (timestamptz), свежие сверху — для расчёта серии."""
        result = await self.session.execute(
            select(Checkin.created_at)
            .where(Checkin.client_id == client_id, Checkin.status == "approved")
            .order_by(Checkin.created_at.desc())
        )
        return [row[0] for row in result.all()]
