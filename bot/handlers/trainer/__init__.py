"""Тренерский роутер. Фильтр IsTrainer на самом роутере гейтит ВСЮ ветку —
до вложенных роутеров дойдут только апдейты от тренера."""
from aiogram import Router

from bot.filters.is_trainer import IsTrainer

from . import broadcast, clients, programs, reminders, review

router = Router()
router.message.filter(IsTrainer())
router.callback_query.filter(IsTrainer())

router.include_router(review.router)
router.include_router(clients.router)
router.include_router(programs.router)
router.include_router(reminders.router)
router.include_router(broadcast.router)
