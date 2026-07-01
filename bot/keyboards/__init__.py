"""Клавиатуры. Reply-кнопки для флоу, где Telegram отдаёт спец-объект
(контакт, гео) — их нельзя получить обычным текстом."""
from aiogram.types import KeyboardButton, ReplyKeyboardMarkup


def request_contact_kb() -> ReplyKeyboardMarkup:
    """Кнопка «Поделиться контактом». request_contact даёт номер только самого
    пользователя — чужой контакт из книги так не пришлёшь (мы это ещё и проверяем)."""
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📱 Поделиться контактом", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )
