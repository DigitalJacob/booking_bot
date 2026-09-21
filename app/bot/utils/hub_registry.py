from collections.abc import Awaitable, Callable

from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.domain.models import User
from app.infrastructure.database.repositories import Repositories


HubLeaf = Callable[..., Awaitable[None]]

_LEAVES: dict[str, HubLeaf] = {}


def register(action: str, handler: HubLeaf) -> None:
    """Register a hub leaf action (called at handler module import)."""
    _LEAVES[action] = handler


async def dispatch_leaf(
        *,
        action: str,
        message: Message,
        user: User,
        i18n: dict[str, str],
        state: FSMContext,
        repos: Repositories | None = None,
        bot_timezone: str | None = None,
        master_user_id: int | None = None,
        locales: list[str] | None = None,
) -> None:
    """Run a registered leaf if present; no-op for unknown actions."""
    handler = _LEAVES.get(action)
    if handler is None:
        return
    await handler(
        message=message,
        user=user,
        i18n=i18n,
        state=state,
        repos=repos,
        bot_timezone=bot_timezone,
        master_user_id=master_user_id,
        locales=locales,
    )
