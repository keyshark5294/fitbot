"""Репозиторий отчётов (checkins) — ядро продукта: приём фото-отчёта,
очередь тренеру, зачёт/не-зачёт. Фото храним как Telegram file_id (урок Жимова)."""
from datetime import datetime, timezone

from sqlalchemy import func, select

from bot.db.models import Checkin
from bot.db.repositories.base import BaseRepository


class CheckinRepository(BaseRepository):
    async def create(
        self,
        client_id: int,
        kind: str,
        photo_file_id: str | None,
        comment: str | None,
    ) -> Checkin:
        checkin = Checkin(
            client_id=client_id,
            kind=kind,
            photo_file_id=photo_file_id,
            comment=comment,
        )
        self.session.add(checkin)
        await self.session.commit()
        await self.session.refresh(checkin)
        return checkin

    async def get(self, checkin_id: int) -> Checkin | None:
        return await self.session.get(Checkin, checkin_id)

    async def list_pending(self) -> list[Checkin]:
        """Очередь на проверку — старые сверху (FIFO), чтобы никого не забыть."""
        result = await self.session.execute(
            select(Checkin)
            .where(Checkin.status == "pending")
            .order_by(Checkin.created_at.asc())
        )
        return list(result.scalars().all())

    async def set_status(
        self, checkin_id: int, status: str, trainer_comment: str | None = None
    ) -> Checkin | None:
        checkin = await self.session.get(Checkin, checkin_id)
        if checkin is None:
            return None
        checkin.status = status
        checkin.trainer_comment = trainer_comment
        checkin.reviewed_at = datetime.now(timezone.utc)
        await self.session.commit()
        await self.session.refresh(checkin)
        return checkin

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
