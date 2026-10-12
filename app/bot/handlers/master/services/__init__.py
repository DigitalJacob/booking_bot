"""Master services catalogue: list, add, edit, and media."""

from app.bot.handlers.master.services import add as _add_handlers  # noqa: F401
from app.bot.handlers.master.services import edit as _edit_handlers  # noqa: F401
from app.bot.handlers.master.services import list as _list_handlers  # noqa: F401
from app.bot.handlers.master.services import media as _media_handlers  # noqa: F401
from app.bot.handlers.master.services.router import services_router

__all__ = ["services_router"]
