import logging
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.fsm.context import FSMContext
from aiogram.types import TelegramObject, Update, User


logger = logging.getLogger(__name__)


class LangSettingsMiddleware(BaseMiddleware):
    async def __call__(
            self,
            handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
            event: Update,
            data: dict[str, Any],
    ) -> Any:
        user: User | None = data.get("event_from_user")
        if user is None:
            return await handler(event, data)

        if event.callback_query is None:
            return await handler(event, data)

        locales: list[str] = data.get("locales") or []
        state: FSMContext = data["state"]
        user_context_data: dict = await state.get_data()

        callback_data = event.callback_query.data

        if callback_data == "cancel_lang_button_data":
            user_context_data.update(user_lang=None)
            await state.set_data(user_context_data)

        elif (
            callback_data in locales
            and callback_data != user_context_data.get("user_lang")
        ):
            user_context_data.update(user_lang=callback_data)
            await state.set_data(user_context_data)

        return await handler(event, data)
