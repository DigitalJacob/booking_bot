from dataclasses import replace
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
        user = await repos.users.get_user_by_id(user_id=tg_user.id)
        if user is not None and user.username != tg_user.username:
            await repos.users.update_username(
                user_id=tg_user.id,
                username=tg_user.username,
            )
            user = replace(user, username=tg_user.username)

        data["user"] = user
        return await handler(event, data)
