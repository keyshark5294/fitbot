"""Клиентский модуль «Программа»: показать назначенную программу.
Меню-кнопку подвесим позже, пока вход по команде /program."""
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.repositories.clients import ClientRepository
from bot.db.repositories.programs import ProgramRepository
from bot.utils.format import format_program

router = Router()


@router.message(Command("program"))
async def my_program(message: Message, session: AsyncSession) -> None:
    client = await ClientRepository(session).get_by_tg_id(message.from_user.id)
    if client is None:
        await message.answer("Сначала пройди регистрацию — отправь /start.")
        return
    program = await ProgramRepository(session).get_active_for_client(client.id)
    if program is None:
        await message.answer("Тренер пока не назначил тебе программу.")
        return
    await message.answer("📋 Твоя программа:\n\n" + format_program(program))
