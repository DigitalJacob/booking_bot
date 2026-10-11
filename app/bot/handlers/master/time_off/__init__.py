"""Master time off / breaks: list, add flow, and monthly calendar."""

from app.bot.handlers.master.time_off import add as _add_handlers  # noqa: F401
from app.bot.handlers.master.time_off import breaks_calendar as _breaks_calendar  # noqa: F401
from app.bot.handlers.master.time_off import list as _list_handlers  # noqa: F401
from app.bot.handlers.master.time_off.router import time_off_router

__all__ = ["time_off_router"]
