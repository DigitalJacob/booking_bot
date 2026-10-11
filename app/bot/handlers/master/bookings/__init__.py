"""Master bookings: week/month/day lists, cards, and cancel resume hooks."""

# Register callback handlers on bookings_router (import side effects).
# handlers imports list, so list handlers register before action handlers.
from app.bot.handlers.master.bookings import handlers as _action_handlers  # noqa: F401
from app.bot.handlers.master.bookings import list as _list_handlers  # noqa: F401
from app.bot.handlers.master.bookings.router import bookings_router

__all__ = ["bookings_router"]
