from contextlib import suppress
from datetime import datetime, date, time, timedelta
from typing import Literal

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.bot.filters.filters import UserRoleFilter
from app.bot.handlers.common.hub import return_from_list
from app.bot.keyboards.hub import get_hub_dismiss_kb
from app.bot.keyboards.time_off import (
    TimeOffNavCallback,
    TimeOffDeleteCallback,
    TimeOffConfirmCallback,
    format_time_off_line,
    get_time_off_view_kb,
    get_time_off_edit_kb,
    get_time_off_confirm_delete_kb,
    get_time_off_cancel_kb,
)
from app.bot.states.states import TimeOffSG
from app.bot.utils.format import get_zone, combine_local
from app.bot.utils.hub_nav import HUB_MESSAGE_ID_KEY, clear_state_keep_hub
from app.bot.utils.hub_registry import register
from app.domain.enums import UserRole
from app.domain.models import User
from app.infrastructure.database.repositories import Repositories


time_off_router = Router(name="master_time_off")
time_off_router.message.filter(UserRoleFilter(UserRole.MASTER))
time_off_router.callback_query.filter(UserRoleFilter(UserRole.MASTER))

TimeOffMode = Literal["view", "edit"]


def _list_from_dt(bot_timezone: str) -> datetime:
    zone = get_zone(bot_timezone)
    now_local = datetime.now(zone)
    return now_local.replace(hour=0, minute=0, second=0, microsecond=0)


def _today_local(bot_timezone: str) -> date:
    return _list_from_dt(bot_timezone).date()


def _parse_date(value: str) -> date | None:
    value = value.strip()
    for fmt in ("%d.%m.%Y", "%d.%m.%y"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


def _format_day_range(starts: date, ends: date) -> str:
    start_d = starts.strftime("%d.%m.%Y")
    end_d = ends.strftime("%d.%m.%Y")
    if start_d == end_d:
        return start_d
    return f"{start_d}-{end_d}"


def _is_not_modified(exc: TelegramBadRequest) -> bool:
    return "message is not modified" in str(exc).lower()


async def _delete_user_input(message: Message) -> None:
    with suppress(TelegramBadRequest):
        await message.delete()


async def _show_time_off_prompt(
        *,
        message: Message,
        state: FSMContext,
        text: str,
        i18n: dict[str, str],
) -> None:
    """Show FSM prompt on the sticky hub message when possible."""
    data = await state.get_data()
    sticky_id = data.get(HUB_MESSAGE_ID_KEY)
    kb = get_time_off_cancel_kb(i18n)

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


async def show_time_off_list(
        *,
        message: Message,
        repos: Repositories,
        user: User,
        i18n: dict[str, str],
        bot_timezone: str,
        mode: TimeOffMode,
        edit: bool,
        state: FSMContext | None = None,
        prefer_sticky: bool = False,
) -> None:
    rows = await repos.time_off.list_by_master(
        master_user_id=user.user_id,
        from_dt=_list_from_dt(bot_timezone),
    )
    if rows:
        body = "\n".join(
            format_time_off_line(row, i18n, bot_timezone) for row in rows
        )
        text = i18n.get("time_off_header") + "\n\n" + body
    else:
        text = i18n.get("time_off_empty")

    if mode == "view":
        kb = get_time_off_view_kb(i18n)
    else:
        kb = get_time_off_edit_kb(
            rows=rows,
            i18n=i18n,
            bot_timezone=bot_timezone,
        )

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
                # Sticky gone or not editable — fall through and re-point.
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


@time_off_router.callback_query(TimeOffNavCallback.filter(F.action == "close"))
async def process_time_off_close(
        callback: CallbackQuery,
        state: FSMContext,
        user: User,
        i18n: dict[str, str],
) -> None:
    """Back from view → hub schedule section."""
    await return_from_list(
        message=callback.message,
        user=user,
        i18n=i18n,
        state=state,
    )
    await callback.answer()


@time_off_router.callback_query(TimeOffNavCallback.filter(F.action == "edit"))
async def process_time_off_edit(
        callback: CallbackQuery,
        repos: Repositories,
        user: User,
        i18n: dict[str, str],
        bot_timezone: str,
) -> None:
    await show_time_off_list(
        message=callback.message,
        repos=repos,
        user=user,
        i18n=i18n,
        bot_timezone=bot_timezone,
        mode="edit",
        edit=True,
    )
    await callback.answer()


@time_off_router.callback_query(TimeOffNavCallback.filter(F.action == "view"))
async def process_time_off_view(
        callback: CallbackQuery,
        repos: Repositories,
        user: User,
        i18n: dict[str, str],
        bot_timezone: str,
) -> None:
    """Back from edit → read-only view."""
    await show_time_off_list(
        message=callback.message,
        repos=repos,
        user=user,
        i18n=i18n,
        bot_timezone=bot_timezone,
        mode="view",
        edit=True,
    )
    await callback.answer()


@time_off_router.callback_query(TimeOffDeleteCallback.filter())
async def process_time_off_delete(
        callback: CallbackQuery,
        callback_data: TimeOffDeleteCallback,
        repos: Repositories,
        user: User,
        i18n: dict[str, str],
        bot_timezone: str,
) -> None:
    row = await repos.time_off.get(
        time_off_id=callback_data.time_off_id,
    )
    if row is None or row.master_user_id != user.user_id:
        await callback.answer(
            text=i18n.get("time_off_delete_not_found"),
            show_alert=True,
        )
        return

    item = format_time_off_line(row, i18n, bot_timezone).lstrip("• ").strip()
    await callback.message.edit_text(
        text=i18n.get("time_off_confirm_delete").format(item=item),
        reply_markup=get_time_off_confirm_delete_kb(
            time_off_id=row.id,
            i18n=i18n,
        ),
    )
    await callback.answer()


@time_off_router.callback_query(
    TimeOffConfirmCallback.filter(F.action == "yes"),
)
async def process_time_off_delete_yes(
        callback: CallbackQuery,
        callback_data: TimeOffConfirmCallback,
        repos: Repositories,
        user: User,
        i18n: dict[str, str],
        bot_timezone: str,
) -> None:
    deleted = await repos.time_off.delete(
        time_off_id=callback_data.time_off_id,
        master_user_id=user.user_id,
    )
    if not deleted:
        await callback.answer(
            text=i18n.get("time_off_delete_not_found"),
            show_alert=True,
        )
        return
    await callback.answer(text=i18n.get("time_off_deleted"))
    await show_time_off_list(
        message=callback.message,
        repos=repos,
        user=user,
        i18n=i18n,
        bot_timezone=bot_timezone,
        mode="edit",
        edit=True,
    )


@time_off_router.callback_query(
    TimeOffConfirmCallback.filter(F.action == "no"),
)
async def process_time_off_delete_no(
        callback: CallbackQuery,
        repos: Repositories,
        user: User,
        i18n: dict[str, str],
        bot_timezone: str,
) -> None:
    await show_time_off_list(
        message=callback.message,
        repos=repos,
        user=user,
        i18n=i18n,
        bot_timezone=bot_timezone,
        mode="edit",
        edit=True,
    )
    await callback.answer()


@time_off_router.callback_query(TimeOffNavCallback.filter(F.action == "add"))
async def process_time_off_add(
        callback: CallbackQuery,
        state: FSMContext,
        i18n: dict[str, str],
        bot_timezone: str,
) -> None:
    await clear_state_keep_hub(state)
    await state.set_state(TimeOffSG.starts_date)
    example = _today_local(bot_timezone).strftime("%d.%m.%Y")
    await _show_time_off_prompt(
        message=callback.message,
        state=state,
        text=i18n.get("time_off_enter_starts").format(example=example),
        i18n=i18n,
    )
    await callback.answer()


@time_off_router.callback_query(
    TimeOffNavCallback.filter(F.action == "cancel"),
    StateFilter(TimeOffSG),
)
async def process_time_off_cancel_cb(
        callback: CallbackQuery,
        state: FSMContext,
        repos: Repositories,
        user: User,
        i18n: dict[str, str],
        bot_timezone: str,
) -> None:
    await clear_state_keep_hub(state)
    await show_time_off_list(
        message=callback.message,
        repos=repos,
        user=user,
        i18n=i18n,
        bot_timezone=bot_timezone,
        mode="edit",
        edit=True,
        state=state,
        prefer_sticky=True,
    )
    await callback.answer()


@time_off_router.message(StateFilter(TimeOffSG.starts_date))
async def process_time_off_starts(
        message: Message,
        state: FSMContext,
        i18n: dict[str, str],
        bot_timezone: str,
) -> None:
    starts = _parse_date(message.text or "")
    await _delete_user_input(message)
    if starts is None:
        await message.answer(text=i18n.get("time_off_invalid_date"))
        return

    await state.update_data(starts_date=starts.isoformat())
    await state.set_state(TimeOffSG.ends_date)
    example = max(starts, _today_local(bot_timezone)).strftime("%d.%m.%Y")
    await _show_time_off_prompt(
        message=message,
        state=state,
        text=i18n.get("time_off_enter_ends").format(example=example),
        i18n=i18n,
    )


@time_off_router.message(StateFilter(TimeOffSG.ends_date))
async def process_time_off_ends(
        message: Message,
        state: FSMContext,
        repos: Repositories,
        user: User,
        i18n: dict[str, str],
        bot_timezone: str,
) -> None:
    ends = _parse_date(message.text or "")
    await _delete_user_input(message)
    if ends is None:
        await message.answer(text=i18n.get("time_off_invalid_date"))
        return

    data = await state.get_data()
    starts = date.fromisoformat(data["starts_date"])
    if ends < starts:
        await message.answer(text=i18n.get("time_off_invalid_range"))
        return

    if ends < _today_local(bot_timezone):
        await message.answer(text=i18n.get("time_off_invalid_past"))
        return

    starts_at = combine_local(starts, time(0, 0), bot_timezone)
    ends_at = combine_local(ends + timedelta(days=1), time(0, 0), bot_timezone)

    await repos.time_off.add(
        master_user_id=user.user_id,
        starts_at=starts_at,
        ends_at=ends_at,
        note=None,
    )

    when = _format_day_range(starts, ends)
    await clear_state_keep_hub(state)
    await show_time_off_list(
        message=message,
        repos=repos,
        user=user,
        i18n=i18n,
        bot_timezone=bot_timezone,
        mode="edit",
        edit=False,
        state=state,
        prefer_sticky=True,
    )
    await message.answer(
        text=i18n.get("time_off_add_ok").format(when=when),
        reply_markup=get_hub_dismiss_kb(i18n),
    )


async def _hub_time_off(
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
        mode="view",
        edit=True,
    )


register("time_off", _hub_time_off)
