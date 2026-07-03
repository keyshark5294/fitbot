"""Ролевой фильтр «персонал»: тренер (её tg_id) ИЛИ админ-владелец (admin_tg_id,
опц.). Оба получают полный доступ к тренерской ветке; уведомления по-прежнему
идут только тренеру. Вешается на тренерский роутер, остальные апдейты
проваливаются в клиентский."""
from aiogram.filters import BaseFilter
from aiogram.types import CallbackQuery, Message

from bot.config import settings


class IsTrainer(BaseFilter):
    async def __call__(self, event: Message | CallbackQuery) -> bool:
        if event.from_user is None:
            return False
        allowed = {settings.trainer_tg_id}
        if settings.admin_tg_id is not None:
            allowed.add(settings.admin_tg_id)
        return event.from_user.id in allowed
