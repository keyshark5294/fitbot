"""Репозиторий напоминаний. Время храним в ЛОКАЛЬНОМ времени клиента
(reminders.time_local + clients.timezone) — тикер переводит его сам (урок Жимова).
days_of_week — ISO: 1=пн .. 7=вс."""
from datetime import time

from sqlalchemy import select

from bot.db.models import Client, Reminder
from bot.db.repositories.base import BaseRepository


class ReminderRepository(BaseRepository):
    async def create(
        self,
        client_id: int,
        kind: str,
        label: str,
        time_local: time,
        days_of_week: list[int],
    ) -> Reminder:
        reminder = Reminder(
            client_id=client_id,
            kind=kind,
            label=label,
            time_local=time_local,
            days_of_week=days_of_week,
        )
        self.session.add(reminder)
        await self.session.commit()
        await self.session.refresh(reminder)
        return reminder

    async def get(self, reminder_id: int) -> Reminder | None:
        return await self.session.get(Reminder, reminder_id)

    async def list_for_client(self, client_id: int) -> list[Reminder]:
        result = await self.session.execute(
            select(Reminder)
            .where(Reminder.client_id == client_id, Reminder.is_active.is_(True))
            .order_by(Reminder.time_local.asc())
        )
        return list(result.scalars().all())

    async def deactivate(self, reminder_id: int) -> Reminder | None:
        reminder = await self.session.get(Reminder, reminder_id)
        if reminder is None:
            return None
        reminder.is_active = False
        await self.session.commit()
        return reminder

    async def list_active_with_client(self) -> list[tuple[Reminder, Client]]:
        """Для тикера: активные напоминания активных клиентов + их таймзона."""
        result = await self.session.execute(
            select(Reminder, Client)
            .join(Client, Reminder.client_id == Client.id)
            .where(Reminder.is_active.is_(True), Client.status == "active")
        )
        return [(rem, client) for rem, client in result.all()]
