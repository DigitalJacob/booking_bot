from contextlib import suppress

from aiogram import Bot, F, Router
from aiogram.enums import BotCommandScopeType
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import BotCommandScopeChat, CallbackQuery, Message

from app.domain.enums import UserRole
from app.bot.filters.filters import LocaleFilter
from app.bot.keyboards.keyboards import get_lang_settings_kb
from app.bot.keyboards.menu_button import get_main_menu_commands
from app.bot.states.states import LangSG
from app.infrastructure.database.repositories import Repositories
from app.domain.models.user import User


settings_router = Router(name="settings")


@settings_router.message(StateFilter(LangSG.lang), ~CommandStart())
async def process_any_message_when_lang(
        message: Message,
        bot: Bot,
        i18n: dict[str, str],
        state: FSMContext,
        locales: list[str],
) -> None:
    user_id = message.from_user.id
    data = await state.get_data()
    user_lang = data.get("user_lang")

    with suppress(TelegramBadRequest):
        msg_id = data.get("lang_settings_msg_id")
        if msg_id:
            await bot.edit_message_reply_markup(
                chat_id=user_id,
                message_id=msg_id,
            )

    msg = await message.answer(
        text=i18n.get("/lang"),
        reply_markup=get_lang_settings_kb(
            i18n=i18n,
            locales=locales,
            checked=user_lang,
        ),
    )
    await state.update_data(lang_settings_msg_id=msg.message_id)


@settings_router.message(Command(commands="lang"))
async def process_lang_command(
        message: Message,
        i18n: dict[str, str],
        state: FSMContext,
        locales: list[str],
        user: User | None,
) -> None:
    await state.set_state(LangSG.lang)
    user_lang = user.language if user else None

    msg = await message.answer(
        text=i18n.get("/lang"),
        reply_markup=get_lang_settings_kb(
            i18n=i18n,
            locales=locales,
            checked=user_lang,
        ),
    )
    await state.update_data(
        lang_settings_msg_id=msg.message_id,
        user_lang=user_lang,
    )


@settings_router.callback_query(F.data == "save_lang_button_data")
async def process_save_click(
        callback: CallbackQuery,
        bot: Bot,
        i18n: dict[str, str],
        state: FSMContext,
        repos: Repositories,
        user: User | None,
) -> None:
    fsm_data = await state.get_data()
    language = fsm_data.get("user_lang")
    if language:
        await repos.users.change_user_lang(
            language=language,
            user_id=callback.from_user.id,
        )

    await callback.message.edit_text(text=i18n.get("lang_saved"))

    user_role = user.role if user else UserRole.CLIENT
    await bot.set_my_commands(
        commands=get_main_menu_commands(i18n=i18n, role=user_role),
        scope=BotCommandScopeChat(
            type=BotCommandScopeType.CHAT,
            chat_id=callback.from_user.id,
        ),
    )
    await state.update_data(lang_settings_msg_id=None, user_lang=None)
    await state.set_state()


@settings_router.callback_query(F.data == "cancel_lang_button_data")
async def process_cancel_click(
        callback: CallbackQuery,
        i18n: dict[str, str],
        state: FSMContext,
        user: User | None,
) -> None:
    user_lang = user.language if user else None
    lang_label = i18n.get(user_lang) if user_lang else ""
    await callback.message.edit_text(
        text=i18n.get("lang_cancelled").format(lang_label),
    )
    await state.update_data(lang_settings_msg_id=None, user_lang=None)
    await state.set_state()


@settings_router.callback_query(LocaleFilter())
async def process_lang_click(
        callback: CallbackQuery,
        i18n: dict[str, str],
        locales: list[str],
) -> None:
    try:
        await callback.message.edit_text(
            text=i18n.get("/lang"),
            reply_markup=get_lang_settings_kb(
                i18n=i18n,
                locales=locales,
                checked=callback.data,
            ),
        )
    except TelegramBadRequest:
        await callback.answer()
