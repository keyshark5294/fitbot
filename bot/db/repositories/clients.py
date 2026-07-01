"""Пример репозитория — по этому образцу добавляй остальные (programs, checkins, ...)."""
from sqlalchemy import select

from bot.db.models import Client
from bot.db.repositories.base import BaseRepository


class ClientRepository(BaseRepository):
    async def get_by_tg_id(self, tg_id: int) -> Client | None:
        result = await self.session.execute(select(Client).where(Client.tg_id == tg_id))
        return result.scalar_one_or_none()

    async def create(self, tg_id: int, tg_username: str | None, phone: str | None) -> Client:
        client = Client(tg_id=tg_id, tg_username=tg_username, phone=phone)
        self.session.add(client)
        await self.session.commit()
        await self.session.refresh(client)
        return client
