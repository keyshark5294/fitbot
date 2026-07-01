"""Клавиатуры. Reply-кнопки для флоу, где Telegram отдаёт спец-объект
(контакт, гео) — их нельзя получить обычным текстом."""
from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

# Тексты кнопок клиентского меню — константы, чтобы хендлеры ловили по ним же
# (F.text == BTN_...), без рассинхрона строк.
BTN_PROGRAM = "📋 Моя программа"
BTN_CHECKIN = "📸 Отчёт"
BTN_PROFILE = "👤 Профиль"


def client_menu_kb() -> ReplyKeyboardMarkup:
    """Главное меню клиента. Постоянное reply-меню (не one_time)."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_PROGRAM)],
            [KeyboardButton(text=BTN_CHECKIN), KeyboardButton(text=BTN_PROFILE)],
        ],
        resize_keyboard=True,
    )


def request_contact_kb() -> ReplyKeyboardMarkup:
    """Кнопка «Поделиться контактом». request_contact даёт номер только самого
    пользователя — чужой контакт из книги так не пришлёшь (мы это ещё и проверяем)."""
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📱 Поделиться контактом", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )
