from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import Update

from app.infrastructure.database.repositories import Repositories


class UserContextMiddleware(BaseMiddleware):
    async def __call__(
            self,
            handler: Callable[[Update, dict[str, Any]], Awaitable[Any]],
            event: Update,
            data: dict[str, Any],
    ) -> Any:
        tg_user = data.get("event_from_user")
        if tg_user is None:
            data["user"] = None
            return await handler(event, data)

        repos: Repositories = data["repos"]
        data["user"] = await repos.users.get_user(user_id=tg_user.id)
        return await handler(event, data)
