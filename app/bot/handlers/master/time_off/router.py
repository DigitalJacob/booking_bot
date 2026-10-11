from aiogram import Router

from app.bot.filters.filters import UserRoleFilter
from app.domain.enums import UserRole

time_off_router = Router(name="master_time_off")
time_off_router.message.filter(UserRoleFilter(UserRole.MASTER))
time_off_router.callback_query.filter(UserRoleFilter(UserRole.MASTER))
