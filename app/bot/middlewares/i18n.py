import logging
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.fsm.context import FSMContext
from aiogram.types import TelegramObject, User as TgUser

from app.bot.i18n.translator import resolve_i18n
from app.domain.models.user import User


logger = logging.getLogger(__name__)


class TranslatorMiddleware(BaseMiddleware):
    async def __call__(
            self,
            handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
            event: TelegramObject,
            data: dict[str, Any],
    ) -> Any:
        tg_user: TgUser | None = data.get("event_from_user")

        if tg_user is None:
            return await handler(event, data)

        state: FSMContext = data["state"]
        user_context_data = await state.get_data()

        if (user_lang := user_context_data.get("user_lang")) is None:
            db_user: User | None = data.get("user")
            user_lang = db_user.language if db_user else tg_user.language_code

        translations: dict = data["translations"]
        data["i18n"] = resolve_i18n(language=user_lang, translations=translations)

        return await handler(event, data)
