"""Ролевой фильтр. Тренер = один tg_id из конфига. Вешается на тренерский роутер,
non-trainer апдейты проваливаются в клиентский."""
from aiogram.filters import BaseFilter
from aiogram.types import CallbackQuery, Message

from bot.config import settings


class IsTrainer(BaseFilter):
    async def __call__(self, event: Message | CallbackQuery) -> bool:
        return event.from_user is not None and event.from_user.id == settings.trainer_tg_id
