from contextlib import suppress

from aiogram import Bot, Router
from aiogram.enums import BotCommandScopeType
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import BotCommandScopeChat, Message

from app.bot.enums.roles import UserRole
from app.bot.keyboards.menu_button import get_main_menu_commands
from app.bot.states.states import LangSG
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
        language = message.from_user.language_code or translations["default"]
        if language not in translations or language == "default":
            language = translations["default"]

        await repos.users.add_user(
            user_id=message.from_user.id,
            username=message.from_user.username,
            language=language,
            role=user_role,
        )
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
        user_lang = user.language if user else translations["default"]
        i18n = translations.get(user_lang) or translations[translations["default"]]

    await bot.set_my_commands(
        commands=get_main_menu_commands(i18n=i18n, role=user_role),
        scope=BotCommandScopeChat(
            type=BotCommandScopeType.CHAT,
            chat_id=message.from_user.id,
        ),
    )

    await message.answer(text=i18n.get("/start"))
    await state.clear()


@start_router.message(Command(commands="help"))
async def process_help_command(
        message: Message,
        i18n: dict[str, str],
        user: User | None,
) -> None:
    if user and user.role == UserRole.ADMIN:
        await message.answer(text=i18n.get("/help_admin"))
    else:
        await message.answer(text=i18n.get("/help"))
