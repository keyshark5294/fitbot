"""Единственный НЕ-заглушечный хендлер — /start, чтобы каркас сразу отвечал
и было видно, как в хендлер прилетает session. Саму регистрацию дописываешь ты."""
from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.repositories.clients import ClientRepository

router = Router()


@router.message(CommandStart())
async def start(message: Message, session: AsyncSession) -> None:
    clients = ClientRepository(session)
    client = await clients.get_by_tg_id(message.from_user.id)
    if client is None:
        await message.answer(
            "Привет! Ты ещё не зарегистрирован.\n"
            "TODO: запросить контакт и завести клиента в БД."
        )
    else:
        await message.answer("С возвращением! TODO: показать меню.")
