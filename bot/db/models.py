"""ORM-модели (SQLAlchemy 2.0). Зеркалят schema.sql.

Alembic — источник правды по миграциям; эти модели он читает через autogenerate.
Все запросы через ORM параметризуются автоматически — класс SQL-инъекций из Жимова закрыт.
"""
from datetime import datetime, time
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    SmallInteger,
    Text,
    Time,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from bot.db.base import Base


class Client(Base):
    __tablename__ = "clients"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    tg_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    tg_username: Mapped[str | None] = mapped_column(Text)
    full_name: Mapped[str | None] = mapped_column(Text)
    phone: Mapped[str | None] = mapped_column(Text)
    # напоминания считаем в ЛОКАЛЬНОМ времени клиента, не в серверном (баг Жимова)
    timezone: Mapped[str] = mapped_column(Text, nullable=False, server_default="Europe/Moscow")
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default="active")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        CheckConstraint("status IN ('active','paused','stopped')", name="ck_clients_status"),
    )


class Program(Base):
    __tablename__ = "programs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    kind: Mapped[str] = mapped_column(Text, nullable=False, server_default="combined")
    is_archived: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        CheckConstraint("kind IN ('training','nutrition','combined')", name="ck_programs_kind"),
    )


class ProgramItem(Base):
    __tablename__ = "program_items"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    program_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("programs.id", ondelete="CASCADE"), nullable=False
    )
    day_number: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("1"))
    order_index: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    type: Mapped[str] = mapped_column(Text, nullable=False, server_default="exercise")
    title: Mapped[str] = mapped_column(Text, nullable=False)  # «Подтягивания» / «Завтрак»
    details: Mapped[str | None] = mapped_column(Text)  # подходы/повторы или состав приёма
    video_url: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        CheckConstraint("type IN ('exercise','meal','note')", name="ck_program_items_type"),
    )


class Assignment(Base):
    __tablename__ = "assignments"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    client_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("clients.id", ondelete="CASCADE"), nullable=False
    )
    program_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("programs.id", ondelete="RESTRICT"), nullable=False
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))


class Reminder(Base):
    __tablename__ = "reminders"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    client_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("clients.id", ondelete="CASCADE"), nullable=False
    )
    kind: Mapped[str] = mapped_column(Text, nullable=False)  # meal | workout
    label: Mapped[str] = mapped_column(Text, nullable=False)  # «Завтрак», «Тренировка»
    time_local: Mapped[time] = mapped_column(Time, nullable=False)  # локальное время клиента
    days_of_week: Mapped[list[int]] = mapped_column(
        ARRAY(SmallInteger), nullable=False, server_default=text("'{1,2,3,4,5,6,7}'")
    )  # ISO: 1=пн .. 7=вс
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))

    __table_args__ = (
        CheckConstraint("kind IN ('meal','workout')", name="ck_reminders_kind"),
    )


class Checkin(Base):
    """Отчёт клиента — петля аккаунтабилити. Ядро продукта."""

    __tablename__ = "checkins"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    client_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("clients.id", ondelete="CASCADE"), nullable=False
    )
    reminder_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("reminders.id", ondelete="SET NULL")
    )
    kind: Mapped[str] = mapped_column(Text, nullable=False)  # meal | workout | progress
    # Telegram file_id, НЕ локальный путь (баг Жимова: захардкоженный C:\Users\Fortn\...)
    photo_file_id: Mapped[str | None] = mapped_column(Text)
    comment: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default="pending")
    trainer_comment: Mapped[str | None] = mapped_column(Text)  # причина «не зачёт»
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        CheckConstraint("kind IN ('meal','workout','progress')", name="ck_checkins_kind"),
        CheckConstraint(
            "status IN ('pending','approved','rejected')", name="ck_checkins_status"
        ),
    )


class Subscription(Base):
    __tablename__ = "subscriptions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    client_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("clients.id", ondelete="CASCADE"), nullable=False
    )
    plan: Mapped[str] = mapped_column(Text, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default="active")
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    # до когда оплачен доступ / когда следующее списание
    current_period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    yookassa_payment_method_id: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        CheckConstraint(
            "status IN ('active','past_due','canceled')", name="ck_subscriptions_status"
        ),
    )


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    client_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("clients.id", ondelete="CASCADE"), nullable=False
    )
    subscription_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("subscriptions.id", ondelete="SET NULL")
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default="pending")
    yookassa_payment_id: Mapped[str | None] = mapped_column(Text)
    receipt_status: Mapped[str] = mapped_column(Text, nullable=False, server_default="none")  # чек ФНС
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('pending','succeeded','canceled')", name="ck_payments_status"
        ),
        CheckConstraint(
            "receipt_status IN ('none','sent','failed')", name="ck_payments_receipt_status"
        ),
    )
