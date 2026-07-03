"""Репозиторий подписок (ручная оплата). Держим «текущую» подписку клиента
(последняя по started_at) и продлеваем её период при подтверждении оплаты.
Каждое подтверждение пишет строку в payments для истории."""
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import select

from bot.db.models import Client, Payment, Subscription
from bot.db.repositories.base import BaseRepository


class SubscriptionRepository(BaseRepository):
    async def get_current(self, client_id: int) -> Subscription | None:
        result = await self.session.execute(
            select(Subscription)
            .where(Subscription.client_id == client_id)
            .order_by(Subscription.started_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def extend(
        self, client_id: int, plan: str, amount: Decimal, period_days: int
    ) -> Subscription:
        """Продлить активную подписку или завести новую. Новый период считаем от
        max(сейчас, конец текущего) — чтобы досрочная оплата не сгорала."""
        now = datetime.now(timezone.utc)
        sub = await self.get_current(client_id)
        if sub is not None and sub.status != "canceled" and sub.current_period_end > now:
            sub.current_period_end = sub.current_period_end + timedelta(days=period_days)
            sub.status = "active"
        else:
            sub = Subscription(
                client_id=client_id,
                plan=plan,
                amount=amount,
                status="active",
                current_period_end=now + timedelta(days=period_days),
            )
            self.session.add(sub)
        await self.session.flush()  # нужен sub.id для payment
        self.session.add(
            Payment(
                client_id=client_id,
                subscription_id=sub.id,
                amount=amount,
                status="succeeded",
            )
        )
        await self.session.commit()
        await self.session.refresh(sub)
        return sub

    async def set_status(self, subscription_id: int, status: str) -> Subscription | None:
        sub = await self.session.get(Subscription, subscription_id)
        if sub is None:
            return None
        sub.status = status
        await self.session.commit()
        await self.session.refresh(sub)
        return sub

    async def list_active_with_client(self) -> list[tuple[Subscription, Client]]:
        """Текущие активные подписки (последняя на клиента) + клиент — для тикера."""
        result = await self.session.execute(
            select(Subscription, Client)
            .join(Client, Subscription.client_id == Client.id)
            .where(Subscription.status == "active")
            .order_by(Subscription.started_at.desc())
        )
        seen: set[int] = set()
        pairs: list[tuple[Subscription, Client]] = []
        for sub, client in result.all():
            if client.id in seen:
                continue
            seen.add(client.id)
            pairs.append((sub, client))
        return pairs
