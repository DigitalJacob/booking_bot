from aiogram import Router

from app.bot.handlers.master.today import today_router


master_router = Router(name="master")
master_router.include_router(today_router)
