"""Master services catalogue: list, add, edit, and media."""

from app.bot.handlers.master.services import handlers as _handlers  # noqa: F401
from app.bot.handlers.master.services import list as _list_handlers  # noqa: F401
from app.bot.handlers.master.services.router import services_router

__all__ = ["services_router"]
