"""Client booking flow: service → calendar → window → confirm."""

from app.bot.handlers.client.booking import handlers as _handlers  # noqa: F401
from app.bot.handlers.client.booking.router import booking_router

__all__ = ["booking_router"]
