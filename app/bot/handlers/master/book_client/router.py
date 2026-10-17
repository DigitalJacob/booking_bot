from aiogram import Router

from app.bot.filters.filters import UserRoleFilter
from app.domain.enums import UserRole

book_client_router = Router(name="master_book_client")
book_client_router.message.filter(UserRoleFilter(UserRole.MASTER))
book_client_router.callback_query.filter(UserRoleFilter(UserRole.MASTER))
