"""Admin user moderation: lookup, ban/unban, and role changes."""

from app.bot.handlers.admin.users import handlers as _handlers  # noqa: F401
from app.bot.handlers.admin.users.router import admin_users_router

__all__ = ["admin_users_router"]
