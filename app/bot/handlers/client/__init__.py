from aiogram import Router

from app.bot.handlers.client.booking import booking_router
from app.bot.handlers.client.my_bookings import my_bookings_router


client_router = Router(name="client")
client_router.include_router(my_bookings_router)
client_router.include_router(booking_router)
