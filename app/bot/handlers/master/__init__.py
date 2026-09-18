from aiogram import Router

from app.bot.handlers.master.today import today_router
from app.bot.handlers.master.services import services_router
from app.bot.handlers.master.schedule import schedule_router
from app.bot.handlers.master.time_off import time_off_router


master_router = Router(name="master")
master_router.include_router(today_router)
master_router.include_router(services_router)
master_router.include_router(schedule_router)
master_router.include_router(time_off_router)
