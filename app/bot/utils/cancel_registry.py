"""Resume hooks for appointment cancel UI, keyed by cancel source.

Role modules call ``register`` at import time (same idea as ``hub_registry``).
``appointment_cancel`` dispatches by phase without importing role handlers.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Literal

from aiogram import Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from app.domain.models import Appointment, User
from app.infrastructure.database.repositories import Repositories

SOURCE_REMINDER = "reminder"
SOURCE_MY_BOOKINGS = "my_bookings"
SOURCE_MASTER_PUSH = "master_push"
SOURCE_MASTER_BOOKINGS = "master_bookings"

PUSH_SOURCES = frozenset({SOURCE_REMINDER, SOURCE_MASTER_PUSH})
MASTER_SOURCES = frozenset({SOURCE_MASTER_PUSH, SOURCE_MASTER_BOOKINGS})

CancelPhase = Literal["abort", "success", "unavailable"]


@dataclass
class CancelResumeCtx:
    """Shared context for cancel resume hooks."""

    bot: Bot
    chat_id: int
    message_id: int
    repos: Repositories
    user: User
    i18n: dict[str, str]
    translations: dict
    bot_timezone: str
    source: str
    mode: str
    state: FSMContext | None = None
    appointment: Appointment | None = None
    appointment_id: int | None = None
    callback: CallbackQuery | None = None
    reminder_kind: str = ""
    notice_key: str | None = None


CancelHook = Callable[[CancelResumeCtx], Awaitable[None]]


@dataclass(frozen=True)
class CancelSourceHooks:
    on_abort: CancelHook
    on_success: CancelHook
    on_unavailable: CancelHook


_HOOKS: dict[str, CancelSourceHooks] = {}


def register(source: str, hooks: CancelSourceHooks) -> None:
    """Register resume hooks for a cancel source (called at handler import)."""
    _HOOKS[source] = hooks


def get_hooks(source: str) -> CancelSourceHooks | None:
    return _HOOKS.get(source)


async def dispatch(
        source: str,
        phase: CancelPhase,
        ctx: CancelResumeCtx,
) -> bool:
    """Run the hook for ``phase`` if registered. Returns whether a hook ran."""
    hooks = _HOOKS.get(source)
    if hooks is None:
        return False
    if phase == "abort":
        await hooks.on_abort(ctx)
    elif phase == "success":
        await hooks.on_success(ctx)
    else:
        await hooks.on_unavailable(ctx)
    return True
