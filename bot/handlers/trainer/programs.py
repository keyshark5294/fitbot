"""Тренерский модуль «Программы»: создать программу и назначить её клиенту.

Первый заход — программа = название + описание + вид (kind). Пункты (program_items)
добавим позже. Роутер уже под фильтром IsTrainer (см. trainer/__init__.py),
так что отдельно роль тут не проверяем.
"""
import logging

from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.repositories.clients import ClientRepository
from bot.db.repositories.programs import ProgramRepository
from bot.utils.format import KIND_LABELS, format_program

logger = logging.getLogger(__name__)
router = Router()

SKIP_TOKENS = {"/skip", "-", "нет"}


class NewProgram(StatesGroup):
    title = State()
    description = State()
    kind = State()


def _programs_kb(programs: list) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=f"👤 Назначить: {p.title}", callback_data=f"assign:{p.id}")]
        for p in programs
    ]
    rows.append([InlineKeyboardButton(text="➕ Создать программу", callback_data="prog:new")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _kind_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=label, callback_data=f"kind:{value}")]
            for value, label in KIND_LABELS.items()
        ]
    )


@router.message(Command("programs"))
async def programs_list(message: Message, session: AsyncSession) -> None:
    programs = await ProgramRepository(session).list_active()
    if not programs:
        await message.answer(
            "Программ пока нет. Создай первую 👇",
            reply_markup=_programs_kb([]),
        )
        return
    lines = ["<b>Программы</b>", ""]
    for p in programs:
        lines.append(f"• {p.title} — {KIND_LABELS.get(p.kind, p.kind)}")
    await message.answer("\n".join(lines), reply_markup=_programs_kb(programs))


# ---------- создание программы ----------

@router.callback_query(F.data == "prog:new")
async def new_program(cb: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(NewProgram.title)
    await cb.message.answer("Название программы?")
    await cb.answer()


@router.message(NewProgram.title, F.text)
async def program_title(message: Message, state: FSMContext) -> None:
    title = message.text.strip()
    if not title:
        await message.answer("Пустое название не подойдёт. Введи название программы.")
        return
    await state.update_data(title=title)
    await state.set_state(NewProgram.description)
    await message.answer("Описание программы? Пришли текстом или /skip, если без описания.")


@router.message(NewProgram.description, F.text)
async def program_description(message: Message, state: FSMContext) -> None:
    text = message.text.strip()
    description = None if text.lower() in SKIP_TOKENS else text
    await state.update_data(description=description)
    await state.set_state(NewProgram.kind)
    await message.answer("Вид программы?", reply_markup=_kind_kb())


@router.callback_query(NewProgram.kind, F.data.startswith("kind:"))
async def program_kind(cb: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    kind = cb.data.split(":", 1)[1]
    if kind not in KIND_LABELS:
        await cb.answer("Неизвестный вид", show_alert=True)
        return
    data = await state.get_data()
    await state.clear()
    program = await ProgramRepository(session).create(
        title=data["title"], description=data.get("description"), kind=kind
    )
    await cb.message.edit_reply_markup(reply_markup=None)
    await cb.message.answer(
        "✅ Программа создана:\n\n" + format_program(program),
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="👤 Назначить клиенту", callback_data=f"assign:{program.id}")]
            ]
        ),
    )
    await cb.answer()


# ---------- назначение клиенту ----------

@router.callback_query(F.data.startswith("assign:"))
async def assign_pick_client(cb: CallbackQuery, session: AsyncSession) -> None:
    program_id = int(cb.data.split(":", 1)[1])
    program = await ProgramRepository(session).get(program_id)
    if program is None:
        await cb.answer("Программа не найдена", show_alert=True)
        return
    clients = await ClientRepository(session).list_all()
    if not clients:
        await cb.answer("Пока нет ни одного клиента", show_alert=True)
        return
    rows = [
        [InlineKeyboardButton(
            text=c.full_name or f"id{c.tg_id}",
            callback_data=f"assignto:{program_id}:{c.id}",
        )]
        for c in clients
    ]
    await cb.message.answer(
        f"Кому назначить «{program.title}»?",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
    )
    await cb.answer()


@router.callback_query(F.data.startswith("assignto:"))
async def assign_do(cb: CallbackQuery, session: AsyncSession, bot: Bot) -> None:
    _, program_id_s, client_id_s = cb.data.split(":")
    program_id, client_id = int(program_id_s), int(client_id_s)

    programs = ProgramRepository(session)
    program = await programs.get(program_id)
    client = await ClientRepository(session).get(client_id)
    if program is None or client is None:
        await cb.answer("Программа или клиент не найдены", show_alert=True)
        return

    await programs.assign(client_id=client.id, program_id=program.id)
    await cb.message.edit_reply_markup(reply_markup=None)
    await cb.message.answer(
        f"✅ «{program.title}» назначена клиенту {client.full_name or client.tg_id}."
    )
    await cb.answer()

    # уведомляем клиента и сразу показываем программу
    try:
        await bot.send_message(
            client.tg_id,
            "🎯 Тренер назначил тебе программу:\n\n" + format_program(program),
        )
    except Exception:
        logger.exception("Не удалось уведомить клиента id=%s о назначении", client.id)
