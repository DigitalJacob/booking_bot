from contextlib import suppress

from aiogram import Bot, Router
from aiogram.enums import BotCommandScopeType
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, CommandStart
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


async def _ensure_registered_user(
        *,
        message: Message,
        admin_ids: list[int],
        translations: dict,
        repos: Repositories,
        user: User | None,
) -> tuple[User, UserRole]:
    if user is not None:
        return user, user.role

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
    return user, user_role


async def _set_chat_commands(
        *,
        bot: Bot,
        chat_id: int,
        i18n: dict[str, str],
        role: UserRole,
) -> None:
    await bot.set_my_commands(
        commands=get_main_menu_commands(i18n=i18n, role=role),
        scope=BotCommandScopeChat(
            type=BotCommandScopeType.CHAT,
            chat_id=chat_id,
        ),
    )


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
    user, user_role = await _ensure_registered_user(
        message=message,
        admin_ids=admin_ids,
        translations=translations,
        repos=repos,
        user=user,
    )

    if await state.get_state() == LangSG.lang:
        data = await state.get_data()
        with suppress(TelegramBadRequest):
            msg_id = data.get("lang_settings_msg_id")
            if msg_id:
                await bot.edit_message_reply_markup(
                    chat_id=message.from_user.id,
                    message_id=msg_id,
                )
        i18n = resolve_i18n(
            language=user.language if user else None,
            translations=translations,
        )

    await _set_chat_commands(
        bot=bot,
        chat_id=message.from_user.id,
        i18n=i18n,
        role=user_role,
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


@start_router.message(Command("menu"))
async def process_menu_command(
        message: Message,
        bot: Bot,
        i18n: dict[str, str],
        state: FSMContext,
        admin_ids: list[int],
        translations: dict,
        repos: Repositories,
        user: User | None,
) -> None:
    user, user_role = await _ensure_registered_user(
        message=message,
        admin_ids=admin_ids,
        translations=translations,
        repos=repos,
        user=user,
    )
    i18n = resolve_i18n(
        language=user.language if user else None,
        translations=translations,
    )

    await _set_chat_commands(
        bot=bot,
        chat_id=message.from_user.id,
        i18n=i18n,
        role=user_role,
    )
    await clear_state_keep_hub(state)
    await show_hub(
        message=message,
        user=user,
        i18n=i18n,
        state=state,
        force_new=True,
    )
    with suppress(TelegramBadRequest):
        await message.delete()
