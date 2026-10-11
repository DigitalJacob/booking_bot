from aiogram import Router

from app.bot.filters.filters import UserRoleFilter
from app.domain.enums import UserRole

work_days_router = Router(name="master_work_days")
work_days_router.message.filter(UserRoleFilter(UserRole.MASTER))
work_days_router.callback_query.filter(UserRoleFilter(UserRole.MASTER))
