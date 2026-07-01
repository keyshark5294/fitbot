"""Клиентский модуль «Отчёт» (checkins) — ядро продукта.
Флоу: кнопка «Отчёт» → вид → фото → комментарий → в БД (pending) → тренеру
в очередь с кнопками зачёт/не-зачёт. Фото — Telegram file_id, не путь (урок Жимова)."""
import logging
from html import escape

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config import settings
from bot.db.repositories.checkins import CheckinRepository
from bot.db.repositories.clients import ClientRepository
from bot.keyboards import BTN_CHECKIN
from bot.utils.format import CHECKIN_KIND_LABELS

logger = logging.getLogger(__name__)
router = Router()

SKIP_TOKENS = {"/skip", "-", "нет"}


class NewCheckin(StatesGroup):
    kind = State()
    photo = State()
    comment = State()


def _kind_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=label, callback_data=f"ckind:{value}")]
            for value, label in CHECKIN_KIND_LABELS.items()
        ]
    )


@router.message(F.text == BTN_CHECKIN)
async def checkin_start(message: Message, session: AsyncSession, state: FSMContext) -> None:
    client = await ClientRepository(session).get_by_tg_id(message.from_user.id)
    if client is None:
        await message.answer("Сначала пройди регистрацию — отправь /start.")
        return
    await state.set_state(NewCheckin.kind)
    await message.answer("Что за отчёт?", reply_markup=_kind_kb())


@router.callback_query(F.data.startswith("remck:"))
async def checkin_from_reminder(cb: CallbackQuery, state: FSMContext) -> None:
    """Кнопка «Отправить отчёт» из напоминания — тип уже известен, сразу к фото."""
    kind = cb.data.split(":", 1)[1]
    if kind not in CHECKIN_KIND_LABELS:
        kind = "workout"
    await state.set_state(NewCheckin.photo)
    await state.update_data(kind=kind)
    await cb.message.answer("Пришли фото отчёта 📸")
    await cb.answer()


@router.callback_query(NewCheckin.kind, F.data.startswith("ckind:"))
async def checkin_kind(cb: CallbackQuery, state: FSMContext) -> None:
    kind = cb.data.split(":", 1)[1]
    if kind not in CHECKIN_KIND_LABELS:
        await cb.answer("Неизвестный вид", show_alert=True)
        return
    await state.update_data(kind=kind)
    await state.set_state(NewCheckin.photo)
    await cb.message.edit_reply_markup(reply_markup=None)
    await cb.message.answer("Пришли фото отчёта 📸")
    await cb.answer()


@router.message(NewCheckin.photo, F.photo)
async def checkin_photo(message: Message, state: FSMContext) -> None:
    # берём самый крупный размер
    await state.update_data(photo_file_id=message.photo[-1].file_id)
    await state.set_state(NewCheckin.comment)
    await message.answer("Добавь комментарий или отправь /skip.")


@router.message(NewCheckin.photo)
async def checkin_photo_expected(message: Message) -> None:
    await message.answer("Нужно фото. Пришли снимок отчёта 📸")


@router.message(NewCheckin.comment, F.text)
async def checkin_comment(
    message: Message, session: AsyncSession, state: FSMContext, bot: Bot
) -> None:
    text = message.text.strip()
    comment = None if text.lower() in SKIP_TOKENS else text

    client = await ClientRepository(session).get_by_tg_id(message.from_user.id)
    if client is None:
        await state.clear()
        await message.answer("Сначала пройди регистрацию — отправь /start.")
        return

    data = await state.get_data()
    await state.clear()
    checkin = await CheckinRepository(session).create(
        client_id=client.id,
        kind=data["kind"],
        photo_file_id=data.get("photo_file_id"),
        comment=comment,
    )

    await message.answer("✅ Отчёт отправлен тренеру. Жди проверки!")

    # отправляем тренеру в очередь: фото + подпись + кнопки зачёт/не-зачёт
    kind_label = CHECKIN_KIND_LABELS.get(checkin.kind, checkin.kind)
    caption = f"📥 Новый отчёт: <b>{escape(client.full_name or str(client.tg_id))}</b>\n{kind_label}"
    if comment:
        caption += f"\n\n{escape(comment)}"
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Зачёт", callback_data=f"ckok:{checkin.id}"),
        InlineKeyboardButton(text="❌ Не зачёт", callback_data=f"ckno:{checkin.id}"),
    ]])
    try:
        if checkin.photo_file_id:
            await bot.send_photo(
                settings.trainer_tg_id, checkin.photo_file_id, caption=caption, reply_markup=kb
            )
        else:
            await bot.send_message(settings.trainer_tg_id, caption, reply_markup=kb)
    except Exception:
        logger.exception("Не удалось отправить отчёт id=%s тренеру", checkin.id)
