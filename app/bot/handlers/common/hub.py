from contextlib import suppress

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.bot.keyboards.hub import (
    HubCallback,
    get_hub_back_home_kb,
    get_hub_home_kb,
    get_hub_moderation_kb,
    get_hub_profile_kb,
    get_hub_schedule_kb,
    get_hub_settings_kb,
)
from app.bot.utils.hub_nav import (
    HUB_MESSAGE_ID_KEY,
    clear_state_keep_hub,
    show_hub,
)
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
    """Open a hub screen or wired list by action name (edit-in-place)."""
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
        if role == UserRole.MASTER:
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

    if action == "moderation":
        if role != UserRole.ADMIN:
            return
        await state.update_data(hub_screen="moderation", hub_back="root")
        await message.edit_text(
            text=i18n.get("hub_moderation_title"),
            reply_markup=get_hub_moderation_kb(i18n),
        )
        return

    if action == "help":
        await state.update_data(hub_screen="help", hub_back="settings")
        await message.edit_text(
            text=_help_text(role, i18n),
            reply_markup=get_hub_back_home_kb(i18n),
        )
        return

    if action == "services":
        if role != UserRole.MASTER or repos is None:
            return
        from app.bot.handlers.master.services import show_services_list

        await state.update_data(
            hub_screen="services",
            hub_back="root",
            list_return="root",
        )
        await show_services_list(
            message=message,
            repos=repos,
            user=user,
            i18n=i18n,
            edit=True,
        )
        return

    if action == "working_hours":
        if role != UserRole.MASTER or repos is None:
            return
        from app.bot.handlers.master.schedule import show_schedule_list

        await state.update_data(
            hub_screen="working_hours",
            hub_back="schedule",
            list_return="schedule",
        )
        await show_schedule_list(
            message=message,
            repos=repos,
            user=user,
            i18n=i18n,
            edit=True,
        )
        return

    if action == "time_off":
        if role != UserRole.MASTER or repos is None or bot_timezone is None:
            return
        from app.bot.handlers.master.time_off import show_time_off_list

        await state.update_data(
            hub_screen="time_off",
            hub_back="schedule",
            list_return="schedule",
        )
        await show_time_off_list(
            message=message,
            repos=repos,
            user=user,
            i18n=i18n,
            bot_timezone=bot_timezone,
            edit=True,
        )
        return

    if action == "my_bookings":
        if repos is None:
            return
        from app.bot.handlers.client.my_bookings import send_my_bookings

        await state.update_data(hub_screen="my_bookings", hub_back="root")
        await message.edit_text(
            text=i18n.get("hub_my_bookings_opened"),
            reply_markup=get_hub_home_kb(i18n),
        )
        await send_my_bookings(
            message=message,
            repos=repos,
            user=user,
            i18n=i18n,
            bot_timezone=bot_timezone or "UTC",
            skip_header=True,
        )
        return

    if action in ("admin_user", "admin_ban", "admin_unban", "admin_set_role"):
        if role != UserRole.ADMIN:
            return
        from app.bot.handlers.admin.users import start_admin_mod_flow

        action_map = {
            "admin_user": "user",
            "admin_ban": "ban",
            "admin_unban": "unban",
            "admin_set_role": "set_role",
        }
        await start_admin_mod_flow(
            message=message,
            state=state,
            i18n=i18n,
            action=action_map[action],
        )
        return

    if action == "book":
        if role == UserRole.MASTER or repos is None or master_user_id is None:
            return
        from app.bot.handlers.client.booking import start_booking_flow

        await state.update_data(hub_screen="book", hub_back="root")
        await start_booking_flow(
            message=message,
            i18n=i18n,
            state=state,
            repos=repos,
            user=user,
            master_user_id=master_user_id,
            edit=True,
        )
        return

    if action == "today":
        if role != UserRole.MASTER or repos is None or bot_timezone is None:
            return
        from app.bot.handlers.master.today import send_today

        await state.update_data(hub_screen="today", hub_back="root")
        await message.edit_text(
            text=i18n.get("hub_today_opened"),
            reply_markup=get_hub_home_kb(i18n),
        )
        await send_today(
            message=message,
            repos=repos,
            user=user,
            i18n=i18n,
            bot_timezone=bot_timezone,
        )
        return

    if action == "profile_show":
        if role == UserRole.MASTER:
            return
        from app.bot.handlers.client.profile import format_profile_card, start_profile_flow

        await state.update_data(hub_screen="profile_show", hub_back="profile")
        if not user.profile_complete:
            await message.edit_text(
                text=i18n.get("hub_profile_incomplete"),
                reply_markup=get_hub_home_kb(i18n),
            )
            await start_profile_flow(
                message=message,
                state=state,
                i18n=i18n,
                resume_book=False,
            )
            return
        await message.edit_text(
            text=format_profile_card(user, i18n),
            reply_markup=get_hub_back_home_kb(i18n),
        )
        return

    if action == "profile_edit":
        if role == UserRole.MASTER:
            return
        from app.bot.handlers.client.profile import start_profile_flow

        await state.update_data(hub_screen="profile_edit", hub_back="profile")
        await message.edit_text(
            text=i18n.get("hub_profile_edit_started"),
            reply_markup=get_hub_home_kb(i18n),
        )
        await start_profile_flow(
            message=message,
            state=state,
            i18n=i18n,
            resume_book=False,
        )
        return

    if action == "lang":
        if locales is None:
            return
        from app.bot.handlers.common.settings import start_lang_settings

        await state.update_data(hub_screen="lang", hub_back="settings")
        await start_lang_settings(
            message=message,
            i18n=i18n,
            state=state,
            locales=locales,
            user=user,
            edit=True,
        )
        return


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
