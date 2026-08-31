from aiogram import Router

from app.bot.handlers.client.booking import booking_router


client_router = Router(name="client")
client_router.include_router(booking_router)
