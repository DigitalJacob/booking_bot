from contextlib import suppress

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.bot.keyboards.hub import (
    HubCallback,
    get_hub_back_home_kb,
    get_hub_profile_kb,
    get_hub_schedule_kb,
    get_hub_settings_kb,
)
from app.bot.utils.hub_nav import (
    HUB_MESSAGE_ID_KEY,
    clear_state_keep_hub,
    show_hub,
)
from app.bot.utils.hub_registry import dispatch_leaf
from app.domain.enums import UserRole
from app.domain.models import User
from app.infrastructure.database.repositories import Repositories


hub_router = Router(name="hub")


def _help_text(role: UserRole | None, i18n: dict[str, str]) -> str:
    if role == UserRole.MASTER:
        return i18n.get("/help_master")
    if role == UserRole.ADMIN:
        return i18n.get("/help_admin")
    return i18n.get("/help")


async def show_hub_screen(
        *,
        message: Message,
        user: User,
        i18n: dict[str, str],
        state: FSMContext,
        action: str,
        repos: Repositories | None = None,
        bot_timezone: str | None = None,
        master_user_id: int | None = None,
        locales: list[str] | None = None,
) -> None:
    """Open a hub section or a registered leaf by action name."""
    role = user.role

    if action == "root":
        await show_hub(
            message=message,
            user=user,
            i18n=i18n,
            state=state,
        )
        return

    if action == "settings":
        await state.update_data(hub_screen="settings", hub_back="root")
        await message.edit_text(
            text=i18n.get("hub_settings_title"),
            reply_markup=get_hub_settings_kb(i18n),
        )
        return

    if action == "profile":
        if role != UserRole.CLIENT:
            return
        await state.update_data(hub_screen="profile", hub_back="root")
        await message.edit_text(
            text=i18n.get("hub_profile_title"),
            reply_markup=get_hub_profile_kb(i18n),
        )
        return

    if action == "schedule":
        if role != UserRole.MASTER:
            return
        await state.update_data(hub_screen="schedule", hub_back="root")
        await message.edit_text(
            text=i18n.get("hub_schedule_title"),
            reply_markup=get_hub_schedule_kb(i18n),
        )
        return

    if action == "help":
        await state.update_data(hub_screen="help", hub_back="settings")
        await message.edit_text(
            text=_help_text(role, i18n),
            reply_markup=get_hub_back_home_kb(i18n),
        )
        return

    await dispatch_leaf(
        action=action,
        message=message,
        user=user,
        i18n=i18n,
        state=state,
        repos=repos,
        bot_timezone=bot_timezone,
        master_user_id=master_user_id,
        locales=locales,
    )


async def return_from_list(
        *,
        message: Message,
        user: User,
        i18n: dict[str, str],
        state: FSMContext,
) -> None:
    """Close a list UI: back to schedule section or hub root."""
    data = await state.get_data()
    target = data.get("list_return") or "root"
    await show_hub_screen(
        message=message,
        user=user,
        i18n=i18n,
        state=state,
        action=target,
    )


@hub_router.message(Command(commands="menu"))
async def process_menu_command(
        message: Message,
        state: FSMContext,
        user: User | None,
        i18n: dict[str, str],
) -> None:
    if user is None:
        await message.answer(text=i18n.get("book_need_start"))
        return
    await clear_state_keep_hub(state)
    await show_hub(
        message=message,
        user=user,
        i18n=i18n,
        state=state,
        force_new=True,
    )


@hub_router.callback_query(HubCallback.filter(F.action == "dismiss"))
async def process_hub_dismiss(
        callback: CallbackQuery,
        state: FSMContext,
        user: User | None,
        i18n: dict[str, str],
) -> None:
    """OK on book_ok / status push: restore sticky hub or delete the push."""
    if user is None:
        await callback.answer(text=i18n.get("book_need_start"), show_alert=True)
        return

    data = await state.get_data()
    sticky_id = data.get(HUB_MESSAGE_ID_KEY)
    msg_id = callback.message.message_id

    if sticky_id is not None and msg_id == sticky_id:
        await show_hub(
            message=callback.message,
            user=user,
            i18n=i18n,
            state=state,
        )
    else:
        with suppress(TelegramBadRequest):
            await callback.message.delete()

    await callback.answer()


@hub_router.callback_query(HubCallback.filter(F.action == "root"))
async def process_hub_root(
        callback: CallbackQuery,
        state: FSMContext,
        user: User | None,
        i18n: dict[str, str],
) -> None:
    if user is None:
        await callback.answer(text=i18n.get("book_need_start"), show_alert=True)
        return
    hub_id = await show_hub(
        message=callback.message,
        user=user,
        i18n=i18n,
        state=state,
    )
    if callback.message.message_id != hub_id:
        with suppress(TelegramBadRequest):
            await callback.message.edit_reply_markup(reply_markup=None)
    await callback.answer()


@hub_router.callback_query(HubCallback.filter(F.action == "back"))
async def process_hub_back(
        callback: CallbackQuery,
        state: FSMContext,
        user: User | None,
        i18n: dict[str, str],
        repos: Repositories,
        bot_timezone: str,
        master_user_id: int,
        locales: list[str],
) -> None:
    if user is None:
        await callback.answer(text=i18n.get("book_need_start"), show_alert=True)
        return

    data = await state.get_data()
    target = data.get("hub_back") or "root"
    await show_hub_screen(
        message=callback.message,
        user=user,
        i18n=i18n,
        state=state,
        action=target,
        repos=repos,
        bot_timezone=bot_timezone,
        master_user_id=master_user_id,
        locales=locales,
    )
    await callback.answer()


@hub_router.callback_query(HubCallback.filter())
async def process_hub_action(
        callback: CallbackQuery,
        callback_data: HubCallback,
        state: FSMContext,
        user: User | None,
        i18n: dict[str, str],
        repos: Repositories,
        bot_timezone: str,
        master_user_id: int,
        locales: list[str],
) -> None:
    if user is None:
        await callback.answer(text=i18n.get("book_need_start"), show_alert=True)
        return

    await show_hub_screen(
        message=callback.message,
        user=user,
        i18n=i18n,
        state=state,
        action=callback_data.action,
        repos=repos,
        bot_timezone=bot_timezone,
        master_user_id=master_user_id,
        locales=locales,
    )
    await callback.answer()
