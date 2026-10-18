"""Master book-for-client flow: lookup, create manual client, slot funnel."""

from app.bot.handlers.master.book_client import create as _create_handlers  # noqa: F401
from app.bot.handlers.master.book_client import funnel as _funnel_handlers  # noqa: F401
from app.bot.handlers.master.book_client import lookup as _lookup_handlers  # noqa: F401
from app.bot.handlers.master.book_client.router import book_client_router

__all__ = ["book_client_router"]
