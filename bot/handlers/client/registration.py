"""Регистрация клиента: /start → имя → контакт → запись в БД → уведомление тренеру.

Состояние шага держим в FSM aiogram, НЕ в колонке БД (урок Жимова).
Контакт принимаем только СВОЙ: request_contact у Telegram отдаёт номер самого
пользователя, но пересланный/из книги контакт другого человека отсекаем по user_id.
"""
import logging

from aiogram import Bot, F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, ReplyKeyboardRemove
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config import settings
from bot.db.repositories.clients import ClientRepository
from bot.keyboards import request_contact_kb

logger = logging.getLogger(__name__)
router = Router()


class Registration(StatesGroup):
    waiting_name = State()
    waiting_contact = State()


@router.message(CommandStart())
async def start(message: Message, session: AsyncSession, state: FSMContext) -> None:
    clients = ClientRepository(session)
    client = await clients.get_by_tg_id(message.from_user.id)
    if client is not None:
        # повторный /start уже зарегистрированного не плодит дублей
        await state.clear()
        await message.answer(
            f"С возвращением, {client.full_name or 'спортсмен'}! "
            "Ты уже зарегистрирован.\nTODO: показать меню клиента.",
            reply_markup=ReplyKeyboardRemove(),
        )
        return

    await state.set_state(Registration.waiting_name)
    await message.answer(
        "Привет! Это бот твоего тренера.\nКак тебя зовут? Напиши имя (и фамилию, если хочешь)."
    )


@router.message(Registration.waiting_name, F.text)
async def got_name(message: Message, state: FSMContext) -> None:
    name = message.text.strip()
    if not name:
        await message.answer("Пустое имя не подойдёт — напиши, как тебя зовут.")
        return
    await state.update_data(full_name=name)
    await state.set_state(Registration.waiting_contact)
    await message.answer(
        f"Приятно познакомиться, {name}!\n"
        "Теперь поделись номером телефона кнопкой ниже — по нему тренер тебя найдёт.",
        reply_markup=request_contact_kb(),
    )


@router.message(Registration.waiting_contact, F.contact)
async def got_contact(
    message: Message, session: AsyncSession, state: FSMContext, bot: Bot
) -> None:
    contact = message.contact
    # отсекаем чужой контакт из телефонной книги: свой всегда с user_id владельца
    if contact.user_id != message.from_user.id:
        await message.answer(
            "Это чужой контакт. Нажми кнопку ниже — Telegram пришлёт именно твой номер.",
            reply_markup=request_contact_kb(),
        )
        return

    clients = ClientRepository(session)
    # защита от гонки/двойного тапа: вдруг клиент уже успел создаться
    if await clients.get_by_tg_id(message.from_user.id) is not None:
        await state.clear()
        await message.answer(
            "Ты уже зарегистрирован. TODO: показать меню клиента.",
            reply_markup=ReplyKeyboardRemove(),
        )
        return

    data = await state.get_data()
    client = await clients.create(
        tg_id=message.from_user.id,
        tg_username=message.from_user.username,
        full_name=data.get("full_name"),
        phone=contact.phone_number,
    )
    await state.clear()

    await message.answer(
        f"Готово, {client.full_name or 'спортсмен'}! Ты зарегистрирован.\n"
        "TODO: показать меню клиента.",
        reply_markup=ReplyKeyboardRemove(),
    )

    # уведомляем тренера о новом клиенте
    username = f" (@{client.tg_username})" if client.tg_username else ""
    try:
        await bot.send_message(
            settings.trainer_tg_id,
            f"🆕 Новый клиент: <b>{client.full_name or 'без имени'}</b>{username}\n"
            f"Телефон: {client.phone}",
        )
    except Exception:
        logger.exception("Не удалось уведомить тренера о новом клиенте id=%s", client.id)


@router.message(Registration.waiting_contact)
async def contact_expected(message: Message) -> None:
    await message.answer(
        "Нужен номер телефона. Нажми кнопку «Поделиться контактом» ниже.",
        reply_markup=request_contact_kb(),
    )
