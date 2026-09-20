from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.bot.keyboards.hub import (
    HubCallback,
    get_hub_back_home_kb,
    get_hub_home_kb,
    get_hub_moderation_kb,
    get_hub_profile_kb,
    get_hub_root_kb,
    get_hub_schedule_kb,
    get_hub_settings_kb,
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


def _role(user: User | None) -> UserRole:
    return user.role if user else UserRole.CLIENT


async def show_hub(
        *,
        message: Message,
        user: User | None,
        i18n: dict[str, str],
        state: FSMContext,
        edit: bool,
) -> None:
    await state.update_data(hub_screen="root", hub_back="root", list_return="root")
    text = i18n.get("hub_title")
    kb = get_hub_root_kb(role=_role(user), i18n=i18n)
    if edit:
        await message.edit_text(text=text, reply_markup=kb)
    else:
        await message.answer(text=text, reply_markup=kb)


async def show_hub_screen(
        *,
        message: Message,
        user: User,
        i18n: dict[str, str],
        state: FSMContext,
        action: str,
        repos: Repositories | None = None,
        bot_timezone: str | None = None,
        edit: bool = True,
) -> None:
    """Open a hub screen or wired list by action name (edit-in-place when edit=True)."""
    role = user.role

    if action == "root":
        await show_hub(
            message=message,
            user=user,
            i18n=i18n,
            state=state,
            edit=edit,
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

    # Remaining leaves — temporary slash tip (wired in later commits)
    slash_map: dict[str, tuple[str, str]] = {
        "book": ("/book", "root"),
        "today": ("/today", "root"),
        "profile_show": ("/profile", "profile"),
        "profile_edit": ("/edit_profile", "profile"),
        "lang": ("/lang", "settings"),
    }
    if action in slash_map:
        command, back_screen = slash_map[action]
        await state.update_data(hub_screen="slash_tip", hub_back=back_screen)
        await message.edit_text(
            text=i18n.get("hub_use_slash").format(command=command),
            reply_markup=get_hub_back_home_kb(i18n),
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
        edit=True,
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
    await state.clear()
    await show_hub(
        message=message,
        user=user,
        i18n=i18n,
        state=state,
        edit=False,
    )


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
    await show_hub(
        message=callback.message,
        user=user,
        i18n=i18n,
        state=state,
        edit=True,
    )
    await callback.answer()


@hub_router.callback_query(HubCallback.filter(F.action == "back"))
async def process_hub_back(
        callback: CallbackQuery,
        state: FSMContext,
        user: User | None,
        i18n: dict[str, str],
        repos: Repositories,
        bot_timezone: str,
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
        edit=True,
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
        edit=True,
    )
    await callback.answer()
