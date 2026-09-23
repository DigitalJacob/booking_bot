from aiogram import Router

from app.bot.filters.filters import UserRoleFilter
from app.bot.handlers.client.booking import booking_router
from app.bot.handlers.client.my_bookings import my_bookings_router
from app.bot.handlers.client.profile import profile_router
from app.domain.enums import UserRole


client_router = Router(name="client")
client_router.message.filter(UserRoleFilter(UserRole.CLIENT))
client_router.callback_query.filter(UserRoleFilter(UserRole.CLIENT))
client_router.include_router(profile_router)
client_router.include_router(my_bookings_router)
client_router.include_router(booking_router)
