from aiogram import Router

from app.bot.handlers.admin.users import admin_users_router


admin_router = Router(name="admin")
admin_router.include_router(admin_users_router)
