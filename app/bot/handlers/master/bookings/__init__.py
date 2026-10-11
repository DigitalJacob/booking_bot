"""Master bookings: week/month/day lists, cards, and cancel resume hooks."""

# Register callback/hub/cancel handlers (import side effects).
# actions imports list, so list handlers register before action handlers.
from app.bot.handlers.master.bookings import actions as _actions  # noqa: F401
from app.bot.handlers.master.bookings import cancel_hooks as _cancel_hooks  # noqa: F401
from app.bot.handlers.master.bookings import list as _list_handlers  # noqa: F401
from app.bot.handlers.master.bookings.router import bookings_router

__all__ = ["bookings_router"]
