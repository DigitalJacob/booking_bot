import logging
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import Update

from app.domain.models import User


logger = logging.getLogger(__name__)


class BannedMiddleware(BaseMiddleware):
    async def __call__(
            self,
            handler: Callable[[Update, dict[str, Any]], Awaitable[Any]],
            event: Update,
            data: dict[str, Any],
    ) -> Any:
        user: User | None = data.get("user")

        if user is not None and user.banned:
            logger.info("Ignored update from banned user %d", user.user_id)
            return None

        return await handler(event, data)
