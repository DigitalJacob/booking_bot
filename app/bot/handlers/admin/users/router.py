from aiogram import Router

from app.bot.filters.filters import UserRoleFilter
from app.domain.enums import UserRole

admin_users_router = Router(name="admin_users")
admin_users_router.message.filter(UserRoleFilter(UserRole.ADMIN))
admin_users_router.callback_query.filter(UserRoleFilter(UserRole.ADMIN))
