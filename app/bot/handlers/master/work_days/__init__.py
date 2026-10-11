"""Master work days: month picker, calendar, and save flow."""

from app.bot.handlers.master.work_days import handlers as _handlers  # noqa: F401
from app.bot.handlers.master.work_days import months as _months  # noqa: F401
from app.bot.handlers.master.work_days.router import work_days_router

__all__ = ["work_days_router"]
