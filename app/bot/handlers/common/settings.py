from contextlib import suppress

from aiogram import Bot, F, Router
from aiogram.enums import BotCommandScopeType
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import BotCommandScopeChat, CallbackQuery, Message

from app.bot.filters.filters import LocaleFilter
from app.bot.keyboards.lang import get_lang_settings_kb
from app.bot.bot_commands import get_main_menu_commands
from app.bot.states.states import LangSG
from app.bot.utils.hub_nav import HUB_MESSAGE_ID_KEY, clear_state_keep_hub, show_hub
from app.bot.utils.hub_registry import register
from app.domain.enums import UserRole
from app.domain.models.user import User
from app.infrastructure.database.repositories import Repositories


settings_router = Router(name="settings")


async def _finish_lang_flow(
        *,
        message: Message,
        state: FSMContext,
        user: User | None,
        i18n: dict[str, str],
) -> None:
    """Clear lang FSM and restore sticky hub without a notice message."""
    data = await state.get_data()
    sticky_id = data.get(HUB_MESSAGE_ID_KEY)
    lang_msg_id = data.get("lang_settings_msg_id")

    await clear_state_keep_hub(state)
    if user is not None:
        await show_hub(
            message=message,
            user=user,
            i18n=i18n,
            state=state,
        )

    # Lang picker may have opened a non-sticky prompt — remove after hub restore.
    if (
        lang_msg_id is not None
        and sticky_id is not None
        and lang_msg_id != sticky_id
    ):
        with suppress(TelegramBadRequest):
            await message.bot.delete_message(
                chat_id=message.chat.id,
                message_id=lang_msg_id,
            )


@settings_router.message(StateFilter(LangSG.lang), ~CommandStart())
async def process_any_message_when_lang(
        message: Message,
        bot: Bot,
        i18n: dict[str, str],
        state: FSMContext,
        locales: list[str],
) -> None:
    data = await state.get_data()
    user_lang = data.get("user_lang")
    msg_id = data.get("lang_settings_msg_id") or data.get(HUB_MESSAGE_ID_KEY)
    kb = get_lang_settings_kb(
        i18n=i18n,
        locales=locales,
        checked=user_lang,
    )
    text = i18n.get("/lang")

    with suppress(TelegramBadRequest):
        await message.delete()

    if msg_id is not None:
        with suppress(TelegramBadRequest):
            await bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=msg_id,
                text=text,
                reply_markup=kb,
            )
            await state.update_data(lang_settings_msg_id=msg_id)
            return

    msg = await message.answer(text=text, reply_markup=kb)
    await state.update_data(lang_settings_msg_id=msg.message_id)


async def start_lang_settings(
        *,
        message: Message,
        i18n: dict[str, str],
        state: FSMContext,
        locales: list[str],
        user: User | None,
        edit: bool = False,
) -> None:
    await state.set_state(LangSG.lang)
    user_lang = user.language if user else None
    text = i18n.get("/lang")
    kb = get_lang_settings_kb(
        i18n=i18n,
        locales=locales,
        checked=user_lang,
    )
    if edit:
        await message.edit_text(text=text, reply_markup=kb)
        msg_id = message.message_id
    else:
        msg = await message.answer(text=text, reply_markup=kb)
        msg_id = msg.message_id
    await state.update_data(
        lang_settings_msg_id=msg_id,
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
    await callback.answer()
    fsm_data = await state.get_data()
    language = fsm_data.get("user_lang")
    if language:
        await repos.users.change_user_lang(
            language=language,
            user_id=callback.from_user.id,
        )

    user_role = user.role if user else UserRole.CLIENT
    await bot.set_my_commands(
        commands=get_main_menu_commands(i18n=i18n, role=user_role),
        scope=BotCommandScopeChat(
            type=BotCommandScopeType.CHAT,
            chat_id=callback.from_user.id,
        ),
    )
    await _finish_lang_flow(
        message=callback.message,
        state=state,
        user=user,
        i18n=i18n,
    )


@settings_router.callback_query(F.data == "cancel_lang_button_data")
async def process_cancel_click(
        callback: CallbackQuery,
        i18n: dict[str, str],
        state: FSMContext,
        user: User | None,
) -> None:
    await callback.answer()
    await _finish_lang_flow(
        message=callback.message,
        state=state,
        user=user,
        i18n=i18n,
    )


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


async def _hub_lang(
        *,
        message: Message,
        user: User,
        i18n: dict[str, str],
        state: FSMContext,
        locales: list[str] | None = None,
        **_,
) -> None:
    if locales is None:
        return
    await state.update_data(hub_screen="lang", hub_back="settings")
    await start_lang_settings(
        message=message,
        i18n=i18n,
        state=state,
        locales=locales,
        user=user,
        edit=True,
    )


register("lang", _hub_lang)
