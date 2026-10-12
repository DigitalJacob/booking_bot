from aiogram import Router

from app.bot.filters.filters import UserRoleFilter
from app.domain.enums import UserRole

services_router = Router(name="master_services")
services_router.message.filter(UserRoleFilter(UserRole.MASTER))
services_router.callback_query.filter(UserRoleFilter(UserRole.MASTER))
