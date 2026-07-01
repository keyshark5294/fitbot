"""Клиентский модуль «Отчёт» (checkins) — ядро продукта: фото-отчёт клиента
→ очередь тренеру → зачёт/не-зачёт. Полная логика — в отдельной задаче.
Пока кнопка меню отвечает заглушкой, чтобы меню было цельным."""
from aiogram import F, Router
from aiogram.types import Message

from bot.keyboards import BTN_CHECKIN

router = Router()


@router.message(F.text == BTN_CHECKIN)
async def checkin_stub(message: Message) -> None:
    await message.answer("📸 Отчёты скоро появятся — сейчас в разработке.")
