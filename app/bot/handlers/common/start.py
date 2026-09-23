from contextlib import suppress

from aiogram import Bot, Router
from aiogram.enums import BotCommandScopeType
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import BotCommandScopeChat, Message

from app.bot.i18n.translator import resolve_i18n, resolve_language
from app.bot.bot_commands import get_main_menu_commands
from app.bot.states.states import LangSG
from app.bot.utils.hub_nav import clear_state_keep_hub, show_hub
from app.domain.enums import UserRole
from app.domain.models.user import User
from app.infrastructure.database.repositories import Repositories


start_router = Router(name="start")


@start_router.message(CommandStart())
async def process_start_command(
        message: Message,
        bot: Bot,
        i18n: dict[str, str],
        state: FSMContext,
        admin_ids: list[int],
        translations: dict,
        repos: Repositories,
        user: User | None,
) -> None:
    if user is None:
        user_role = (
            UserRole.ADMIN
            if message.from_user.id in admin_ids
            else UserRole.CLIENT
        )
        language = resolve_language(
            language=message.from_user.language_code,
            translations=translations,
        )

        await repos.users.add_user(
            user_id=message.from_user.id,
            username=message.from_user.username,
            language=language,
            role=user_role,
        )
        user = await repos.users.get_user_by_id(user_id=message.from_user.id)
    else:
        user_role = user.role

    if await state.get_state() == LangSG.lang:
        data = await state.get_data()
        with suppress(TelegramBadRequest):
            msg_id = data.get("lang_settings_msg_id")
            if msg_id:
                await bot.edit_message_reply_markup(
                    chat_id=message.from_user.id,
                    message_id=msg_id,
                )
        user_lang = user.language if user else None
        i18n = resolve_i18n(language=user_lang, translations=translations)

    await bot.set_my_commands(
        commands=get_main_menu_commands(i18n=i18n, role=user_role),
        scope=BotCommandScopeChat(
            type=BotCommandScopeType.CHAT,
            chat_id=message.from_user.id,
        ),
    )

    await clear_state_keep_hub(state)
    await show_hub(
        message=message,
        user=user,
        i18n=i18n,
        state=state,
    )
    with suppress(TelegramBadRequest):
        await message.delete()
