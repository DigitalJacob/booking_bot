from contextlib import suppress

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.bot.filters.filters import UserRoleFilter
from app.bot.handlers.common.hub import return_from_list
from app.bot.keyboards.gap import (
    GapNavCallback,
    get_gap_view_kb,
    get_gap_cancel_kb,
)
from app.bot.keyboards.hub import get_hub_dismiss_kb
from app.bot.states.states import GapSG
from app.bot.utils.hub_nav import HUB_MESSAGE_ID_KEY, clear_state_keep_hub
from app.bot.utils.hub_registry import register
from app.domain.enums import UserRole
from app.domain.models import MasterSettings, User
from app.infrastructure.database.repositories import Repositories


gap_router = Router(name="master_gap")
gap_router.message.filter(UserRoleFilter(UserRole.MASTER))
gap_router.callback_query.filter(UserRoleFilter(UserRole.MASTER))

_MAX_GAP_MINUTES = 180


def _is_not_modified(exc: TelegramBadRequest) -> bool:
    return "message is not modified" in str(exc).lower()


async def _delete_user_input(message: Message) -> None:
    with suppress(TelegramBadRequest):
        await message.delete()


async def _ensure_settings(
        *,
        repos: Repositories,
        user: User,
        bot_timezone: str,
) -> MasterSettings:
    settings = await repos.master_settings.get_by_master(
        master_user_id=user.user_id,
    )
    if settings is not None:
        return settings
    return await repos.master_settings.ensure_defaults(
        master_user_id=user.user_id,
        timezone=bot_timezone,
    )


async def _show_gap_prompt(
        *,
        message: Message,
        state: FSMContext,
        text: str,
        i18n: dict[str, str],
) -> None:
    data = await state.get_data()
    sticky_id = data.get(HUB_MESSAGE_ID_KEY)
    kb = get_gap_cancel_kb(i18n)

    if sticky_id is not None:
        try:
            await message.bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=int(sticky_id),
                text=text,
                reply_markup=kb,
            )
            return
        except TelegramBadRequest as exc:
            if _is_not_modified(exc):
                return

    await message.answer(text=text, reply_markup=kb)


async def show_gap_screen(
        *,
        message: Message,
        repos: Repositories,
        user: User,
        i18n: dict[str, str],
        bot_timezone: str,
        edit: bool,
        state: FSMContext | None = None,
        prefer_sticky: bool = False,
) -> None:
    settings = await _ensure_settings(
        repos=repos,
        user=user,
        bot_timezone=bot_timezone,
    )
    text = i18n.get("gap_view").format(minutes=settings.gap_minutes)
    kb = get_gap_view_kb(i18n)

    if prefer_sticky and state is not None:
        data = await state.get_data()
        sticky_id = data.get(HUB_MESSAGE_ID_KEY)
        if sticky_id is not None:
            try:
                await message.bot.edit_message_text(
                    chat_id=message.chat.id,
                    message_id=int(sticky_id),
                    text=text,
                    reply_markup=kb,
                )
                return
            except TelegramBadRequest as exc:
                if _is_not_modified(exc):
                    return
                with suppress(TelegramBadRequest):
                    await message.bot.edit_message_reply_markup(
                        chat_id=message.chat.id,
                        message_id=int(sticky_id),
                        reply_markup=None,
                    )

        sent = await message.answer(text=text, reply_markup=kb)
        await state.update_data({HUB_MESSAGE_ID_KEY: sent.message_id})
        return

    if edit:
        await message.edit_text(text=text, reply_markup=kb)
    else:
        await message.answer(text=text, reply_markup=kb)


@gap_router.callback_query(GapNavCallback.filter(F.action == "close"))
async def process_gap_close(
        callback: CallbackQuery,
        state: FSMContext,
        user: User,
        i18n: dict[str, str],
) -> None:
    await return_from_list(
        message=callback.message,
        user=user,
        i18n=i18n,
        state=state,
    )
    await callback.answer()


@gap_router.callback_query(GapNavCallback.filter(F.action == "edit"))
async def process_gap_edit(
        callback: CallbackQuery,
        state: FSMContext,
        i18n: dict[str, str],
) -> None:
    await clear_state_keep_hub(state)
    await state.set_state(GapSG.value)
    await _show_gap_prompt(
        message=callback.message,
        state=state,
        text=i18n.get("gap_enter"),
        i18n=i18n,
    )
    await callback.answer()


@gap_router.callback_query(
    GapNavCallback.filter(F.action == "cancel"),
    StateFilter(GapSG),
)
async def process_gap_cancel(
        callback: CallbackQuery,
        state: FSMContext,
        repos: Repositories,
        user: User,
        i18n: dict[str, str],
        bot_timezone: str,
) -> None:
    await clear_state_keep_hub(state)
    await show_gap_screen(
        message=callback.message,
        repos=repos,
        user=user,
        i18n=i18n,
        bot_timezone=bot_timezone,
        edit=True,
        state=state,
        prefer_sticky=True,
    )
    await callback.answer()


@gap_router.message(StateFilter(GapSG.value))
async def process_gap_value(
        message: Message,
        state: FSMContext,
        repos: Repositories,
        user: User,
        i18n: dict[str, str],
        bot_timezone: str,
) -> None:
    raw = (message.text or "").strip()
    await _delete_user_input(message)
    if not raw.isdigit():
        await message.answer(text=i18n.get("gap_invalid"))
        return

    gap_minutes = int(raw)
    if gap_minutes > _MAX_GAP_MINUTES:
        await message.answer(
            text=i18n.get("gap_invalid_max").format(max=_MAX_GAP_MINUTES),
        )
        return

    await _ensure_settings(
        repos=repos,
        user=user,
        bot_timezone=bot_timezone,
    )
    updated = await repos.master_settings.update_gap_minutes(
        master_user_id=user.user_id,
        gap_minutes=gap_minutes,
    )
    if updated is None:
        await message.answer(text=i18n.get("gap_save_failed"))
        return

    await clear_state_keep_hub(state)
    await show_gap_screen(
        message=message,
        repos=repos,
        user=user,
        i18n=i18n,
        bot_timezone=bot_timezone,
        edit=False,
        state=state,
        prefer_sticky=True,
    )
    await message.answer(
        text=i18n.get("gap_saved").format(minutes=gap_minutes),
        reply_markup=get_hub_dismiss_kb(i18n),
    )


async def _hub_gap(
        *,
        message: Message,
        user: User,
        i18n: dict[str, str],
        state: FSMContext,
        repos: Repositories | None = None,
        bot_timezone: str | None = None,
        **_,
) -> None:
    if user.role != UserRole.MASTER or repos is None or bot_timezone is None:
        return
    await state.update_data(
        hub_screen="gap",
        hub_back="schedule",
        list_return="schedule",
    )
    await show_gap_screen(
        message=message,
        repos=repos,
        user=user,
        i18n=i18n,
        bot_timezone=bot_timezone,
        edit=True,
    )


register("gap", _hub_gap)
