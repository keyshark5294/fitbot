from aiogram import Router

from . import checkin, payment, profile, program, registration

router = Router()
router.include_router(registration.router)
router.include_router(profile.router)
router.include_router(program.router)
router.include_router(checkin.router)
router.include_router(payment.router)
