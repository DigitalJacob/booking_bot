"""Client booking flow: service → calendar → window → confirm."""

from app.bot.handlers.client.booking import calendar as _calendar  # noqa: F401
from app.bot.handlers.client.booking import handlers as _handlers  # noqa: F401
from app.bot.handlers.client.booking import service as _service  # noqa: F401
from app.bot.handlers.client.booking import window as _window  # noqa: F401
from app.bot.handlers.client.booking.router import booking_router

__all__ = ["booking_router"]
