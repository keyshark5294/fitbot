"""Единый async-движок и фабрика сессий. Один пул на процесс — не новое
соединение на каждый запрос, как было в Жимове."""
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from bot.config import settings

engine = create_async_engine(settings.database_url, pool_pre_ping=True, echo=False)

session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
