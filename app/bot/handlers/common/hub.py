from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.bot.keyboards.hub import (
    HubCallback,
    get_hub_back_home_kb,
    get_hub_moderation_kb,
    get_hub_profile_kb,
    get_hub_root_kb,
    get_hub_schedule_kb,
    get_hub_settings_kb,
)
from app.domain.enums import UserRole
from app.domain.models import User


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
    await state.update_data(hub_screen="root", hub_back="root")
    text = i18n.get("hub_title")
    kb = get_hub_root_kb(role=_role(user), i18n=i18n)
    if edit:
        await message.edit_text(text=text, reply_markup=kb)
    else:
        await message.answer(text=text, reply_markup=kb)


async def _show_section(
        *,
        message: Message,
        i18n: dict[str, str],
        state: FSMContext,
        screen: str,
        title_key: str,
        kb,
) -> None:
    await state.update_data(hub_screen=screen, hub_back="root")
    await message.edit_text(
        text=i18n.get(title_key),
        reply_markup=kb,
    )


async def _show_slash_tip(
        *,
        message: Message,
        i18n: dict[str, str],
        state: FSMContext,
        command: str,
        back_screen: str,
) -> None:
    await state.update_data(hub_screen="slash_tip", hub_back=back_screen)
    await message.edit_text(
        text=i18n.get("hub_use_slash").format(command=command),
        reply_markup=get_hub_back_home_kb(i18n),
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
) -> None:
    if user is None:
        await callback.answer(text=i18n.get("book_need_start"), show_alert=True)
        return

    data = await state.get_data()
    target = data.get("hub_back") or "root"
    await _open_screen(
        callback=callback,
        state=state,
        user=user,
        i18n=i18n,
        action=target,
    )


@hub_router.callback_query(HubCallback.filter())
async def process_hub_action(
        callback: CallbackQuery,
        callback_data: HubCallback,
        state: FSMContext,
        user: User | None,
        i18n: dict[str, str],
) -> None:
    if user is None:
        await callback.answer(text=i18n.get("book_need_start"), show_alert=True)
        return

    await _open_screen(
        callback=callback,
        state=state,
        user=user,
        i18n=i18n,
        action=callback_data.action,
    )


async def _open_screen(
        *,
        callback: CallbackQuery,
        state: FSMContext,
        user: User,
        i18n: dict[str, str],
        action: str,
) -> None:
    role = user.role
    message = callback.message

    if action == "root":
        await show_hub(
            message=message,
            user=user,
            i18n=i18n,
            state=state,
            edit=True,
        )
        await callback.answer()
        return

    if action == "settings":
        await _show_section(
            message=message,
            i18n=i18n,
            state=state,
            screen="settings",
            title_key="hub_settings_title",
            kb=get_hub_settings_kb(i18n),
        )
        await callback.answer()
        return

    if action == "profile":
        if role == UserRole.MASTER:
            await callback.answer()
            return
        await _show_section(
            message=message,
            i18n=i18n,
            state=state,
            screen="profile",
            title_key="hub_profile_title",
            kb=get_hub_profile_kb(i18n),
        )
        await callback.answer()
        return

    if action == "schedule":
        if role != UserRole.MASTER:
            await callback.answer()
            return
        await _show_section(
            message=message,
            i18n=i18n,
            state=state,
            screen="schedule",
            title_key="hub_schedule_title",
            kb=get_hub_schedule_kb(i18n),
        )
        await callback.answer()
        return

    if action == "moderation":
        if role != UserRole.ADMIN:
            await callback.answer()
            return
        await _show_section(
            message=message,
            i18n=i18n,
            state=state,
            screen="moderation",
            title_key="hub_moderation_title",
            kb=get_hub_moderation_kb(i18n),
        )
        await callback.answer()
        return

    if action == "help":
        await state.update_data(hub_screen="help", hub_back="settings")
        await message.edit_text(
            text=_help_text(role, i18n),
            reply_markup=get_hub_back_home_kb(i18n),
        )
        await callback.answer()
        return

    # Leaves wired in later commits — temporary slash tip + Home
    slash_map: dict[str, tuple[str, str]] = {
        "book": ("/book", "root"),
        "my_bookings": ("/my_bookings", "root"),
        "today": ("/today", "root"),
        "services": ("/services", "root"),
        "working_hours": ("/schedule", "schedule"),
        "time_off": ("/time_off", "schedule"),
        "profile_show": ("/profile", "profile"),
        "profile_edit": ("/edit_profile", "profile"),
        "lang": ("/lang", "settings"),
        "admin_user": ("/user", "moderation"),
        "admin_set_role": ("/set_role", "moderation"),
        "admin_ban": ("/ban", "moderation"),
        "admin_unban": ("/unban", "moderation"),
    }
    if action in slash_map:
        command, back_screen = slash_map[action]
        await _show_slash_tip(
            message=message,
            i18n=i18n,
            state=state,
            command=command,
            back_screen=back_screen,
        )
        await callback.answer()
        return

    await callback.answer()
