"""Master book-for-client flow: lookup now; slot funnel and manual create next."""

from app.bot.handlers.master.book_client import lookup as _lookup_handlers  # noqa: F401
from app.bot.handlers.master.book_client.router import book_client_router

__all__ = ["book_client_router"]
