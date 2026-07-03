"""Тренерский модуль «Напоминания»: тренер заводит клиенту напоминания
(тип, метка, время, дни). Вход — из карточки клиента (кнопка «⏰ Напоминания»).
Время — локальное для клиента; тикер (services/scheduler) переведёт его сам."""
from datetime import time

from aiogram import F, Router
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
from bot.db.repositories.reminders import ReminderRepository
from bot.utils.format import DAY_SHORT, REMINDER_KIND_LABELS, format_reminder

router = Router()

# быстрые наборы для кнопок-подсказок при выборе дней
DAY_QUICK: dict[str, list[int]] = {
    "all": [1, 2, 3, 4, 5, 6, 7],
    "week": [1, 2, 3, 4, 5],
}


def _days_kb(selected: set[int]) -> InlineKeyboardMarkup:
    """Клавиатура выбора дней: тап переключает день, ✅ — выбран."""
    def day_btn(n: int) -> InlineKeyboardButton:
        mark = "✅ " if n in selected else ""
        return InlineKeyboardButton(text=f"{mark}{DAY_SHORT[n]}", callback_data=f"rday:{n}")

    return InlineKeyboardMarkup(inline_keyboard=[
        [day_btn(n) for n in (1, 2, 3, 4)],
        [day_btn(n) for n in (5, 6, 7)],
        [
            InlineKeyboardButton(text="Все дни", callback_data="rday:all"),
            InlineKeyboardButton(text="Будни", callback_data="rday:week"),
            InlineKeyboardButton(text="Сброс", callback_data="rday:clear"),
        ],
        [InlineKeyboardButton(text="✅ Готово", callback_data="rdays_done")],
    ])


class NewReminder(StatesGroup):
    kind = State()
    label = State()
    at_time = State()
    days = State()


def _list_kb(client_id: int, reminders: list) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=f"🗑 {format_reminder(r)}", callback_data=f"rem_del:{r.id}")]
        for r in reminders
    ]
    rows.append([InlineKeyboardButton(text="➕ Добавить", callback_data=f"rem_add:{client_id}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


async def _show_list(cb: CallbackQuery, session: AsyncSession, client_id: int) -> None:
    reminders = await ReminderRepository(session).list_for_client(client_id)
    text = "⏰ <b>Напоминания</b>" if reminders else "⏰ Напоминаний нет."
    await cb.message.answer(text, reply_markup=_list_kb(client_id, reminders))


@router.callback_query(F.data.startswith("rem_list:"))
async def reminders_list(cb: CallbackQuery, session: AsyncSession) -> None:
    client_id = int(cb.data.split(":", 1)[1])
    await _show_list(cb, session, client_id)
    await cb.answer()


@router.callback_query(F.data.startswith("rem_del:"))
async def reminder_delete(cb: CallbackQuery, session: AsyncSession) -> None:
    reminder_id = int(cb.data.split(":", 1)[1])
    reminder = await ReminderRepository(session).deactivate(reminder_id)
    if reminder is None:
        await cb.answer("Не найдено", show_alert=True)
        return
    await cb.message.edit_reply_markup(reply_markup=None)
    await cb.answer("Удалено")
    await _show_list(cb, session, reminder.client_id)


# ---------- создание ----------

@router.callback_query(F.data.startswith("rem_add:"))
async def reminder_add(cb: CallbackQuery, state: FSMContext) -> None:
    client_id = int(cb.data.split(":", 1)[1])
    await state.set_state(NewReminder.kind)
    await state.update_data(client_id=client_id)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=label, callback_data=f"rkind:{value}")]
        for value, label in REMINDER_KIND_LABELS.items()
    ])
    await cb.message.answer("Тип напоминания?", reply_markup=kb)
    await cb.answer()


@router.callback_query(NewReminder.kind, F.data.startswith("rkind:"))
async def reminder_kind(cb: CallbackQuery, state: FSMContext) -> None:
    kind = cb.data.split(":", 1)[1]
    if kind not in REMINDER_KIND_LABELS:
        await cb.answer("Неизвестный тип", show_alert=True)
        return
    await state.update_data(kind=kind)
    await state.set_state(NewReminder.label)
    await cb.message.edit_reply_markup(reply_markup=None)
    await cb.message.answer("Название (напр. «Утренняя тренировка»)?")
    await cb.answer()


@router.message(NewReminder.label, F.text)
async def reminder_label(message: Message, state: FSMContext) -> None:
    label = message.text.strip()
    if not label:
        await message.answer("Пустое название не подойдёт. Введи название.")
        return
    await state.update_data(label=label)
    await state.set_state(NewReminder.at_time)
    await message.answer("Во сколько (локальное время клиента)? Формат ЧЧ:ММ, напр. 18:30")


@router.message(NewReminder.at_time, F.text)
async def reminder_time(message: Message, state: FSMContext) -> None:
    parsed = _parse_time(message.text.strip())
    if parsed is None:
        await message.answer("Не понял время. Введи в формате ЧЧ:ММ, напр. 08:00 или 18:30.")
        return
    await state.update_data(hour=parsed.hour, minute=parsed.minute, days=[])
    await state.set_state(NewReminder.days)
    await message.answer(
        "В какие дни? Отметь нужные и нажми «Готово».", reply_markup=_days_kb(set())
    )


@router.callback_query(NewReminder.days, F.data.startswith("rday:"))
async def reminder_days_toggle(cb: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    selected = set(data.get("days", []))
    value = cb.data.split(":", 1)[1]
    if value in DAY_QUICK:
        new_selected = set(DAY_QUICK[value])
    elif value == "clear":
        new_selected = set()
    else:
        new_selected = selected ^ {int(value)}  # переключаем один день

    if new_selected == selected:
        await cb.answer()  # ничего не изменилось — не дёргаем edit
        return
    await state.update_data(days=sorted(new_selected))
    await cb.message.edit_reply_markup(reply_markup=_days_kb(new_selected))
    await cb.answer()


@router.callback_query(NewReminder.days, F.data == "rdays_done")
async def reminder_days_done(cb: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    data = await state.get_data()
    days = sorted(set(data.get("days", [])))
    if not days:
        await cb.answer("Выбери хотя бы один день", show_alert=True)
        return
    await state.clear()

    reminder = await ReminderRepository(session).create(
        client_id=data["client_id"],
        kind=data["kind"],
        label=data["label"],
        time_local=time(hour=data["hour"], minute=data["minute"]),
        days_of_week=days,
    )
    await cb.message.edit_reply_markup(reply_markup=None)
    await cb.message.answer("✅ Напоминание создано:\n" + format_reminder(reminder))
    await cb.answer()
    await _show_list(cb, session, reminder.client_id)


def _parse_time(text: str) -> time | None:
    parts = text.replace(".", ":").split(":")
    if len(parts) != 2:
        return None
    try:
        hour, minute = int(parts[0]), int(parts[1])
    except ValueError:
        return None
    if 0 <= hour <= 23 and 0 <= minute <= 59:
        return time(hour=hour, minute=minute)
    return None
