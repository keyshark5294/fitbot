"""Репозиторий программ и назначений. Первый заход: программа = title+description+kind,
пункты (program_items) добавим позже. Одна активная программа на клиента:
при новом назначении прежние активные гасим (is_active=False)."""
from sqlalchemy import select, update

from bot.db.models import Assignment, Program
from bot.db.repositories.base import BaseRepository


class ProgramRepository(BaseRepository):
    async def create(self, title: str, description: str | None, kind: str) -> Program:
        program = Program(title=title, description=description, kind=kind)
        self.session.add(program)
        await self.session.commit()
        await self.session.refresh(program)
        return program

    async def get(self, program_id: int) -> Program | None:
        return await self.session.get(Program, program_id)

    async def list_active(self) -> list[Program]:
        """Неархивные программы, свежие сверху."""
        result = await self.session.execute(
            select(Program)
            .where(Program.is_archived.is_(False))
            .order_by(Program.created_at.desc())
        )
        return list(result.scalars().all())

    async def assign(self, client_id: int, program_id: int) -> Assignment:
        # одна активная программа на клиента: прежние активные снимаем
        await self.session.execute(
            update(Assignment)
            .where(Assignment.client_id == client_id, Assignment.is_active.is_(True))
            .values(is_active=False)
        )
        assignment = Assignment(client_id=client_id, program_id=program_id)
        self.session.add(assignment)
        await self.session.commit()
        await self.session.refresh(assignment)
        return assignment

    async def get_active_for_client(self, client_id: int) -> Program | None:
        """Текущая программа клиента (последнее активное назначение)."""
        result = await self.session.execute(
            select(Program)
            .join(Assignment, Assignment.program_id == Program.id)
            .where(Assignment.client_id == client_id, Assignment.is_active.is_(True))
            .order_by(Assignment.started_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()
