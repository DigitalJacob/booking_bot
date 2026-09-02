from aiogram import Router

from app.bot.handlers.master.today import today_router
from app.bot.handlers.master.add_slot import add_slot_router
from app.bot.handlers.master.services import services_router


master_router = Router(name="master")
master_router.include_router(today_router)
master_router.include_router(add_slot_router)
master_router.include_router(services_router)
