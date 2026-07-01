"""Сборка всех роутеров. Тренерский идёт первым (он отфильтрован по tg_id),
остальные апдейты проваливаются в клиентский."""
from aiogram import Router

from bot.handlers.client import router as client_router
from bot.handlers.trainer import router as trainer_router

router = Router()
router.include_router(trainer_router)
router.include_router(client_router)
