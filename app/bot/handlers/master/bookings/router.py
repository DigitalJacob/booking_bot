from aiogram import Router

from app.bot.filters.filters import UserRoleFilter
from app.domain.enums import UserRole

bookings_router = Router(name="master_bookings")
bookings_router.message.filter(UserRoleFilter(UserRole.MASTER))
bookings_router.callback_query.filter(UserRoleFilter(UserRole.MASTER))
