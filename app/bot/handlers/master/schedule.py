from datetime import datetime, time
from typing import Literal

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.bot.filters.filters import UserRoleFilter
from app.bot.handlers.common.hub import return_from_list
from app.bot.keyboards.schedule import (
    ScheduleNavCallback,
    ScheduleWeekdayCallback,
    ScheduleDeleteCallback,
    ScheduleConfirmCallback,
    get_weekdays_kb,
    format_interval_line,
    get_schedule_view_kb,
    get_schedule_edit_kb,
    get_schedule_confirm_delete_kb,
    get_schedule_cancel_kb,
    WEEKDAY_KEYS,
)
from app.bot.states.states import ScheduleSG
from app.bot.utils.hub_nav import clear_state_keep_hub
from app.bot.utils.hub_registry import register
from app.domain.enums import UserRole
from app.domain.models import User
from app.infrastructure.database.repositories import Repositories


schedule_router = Router(name="master_schedule")
schedule_router.message.filter(UserRoleFilter(UserRole.MASTER))
schedule_router.callback_query.filter(UserRoleFilter(UserRole.MASTER))

ScheduleMode = Literal["view", "edit"]


def _parse_time(value: str) -> time | None:
    value = value.strip()
    for fmt in ("%H:%M", "%H.%M"):
        try:
            return datetime.strptime(value, fmt).time()
        except ValueError:
            continue
    return None


def _format_hm(value: time) -> str:
    return value.strftime("%H:%M")


def _weekdays_label(selected: set[int], i18n: dict[str, str]) -> str:
    return ", ".join(
        i18n.get(WEEKDAY_KEYS[day])
        for day in sorted(selected)
    )


async def show_schedule_list(
        *,
        message: Message,
        repos: Repositories,
        user: User,
        i18n: dict[str, str],
        mode: ScheduleMode,
        edit: bool,
) -> None:
    rows = await repos.working_hours.list_by_master(
        master_user_id=user.user_id,
    )
    if rows:
        body = "\n".join(format_interval_line(row, i18n) for row in rows)
        text = i18n.get("schedule_header") + "\n\n" + body
    else:
        text = i18n.get("schedule_empty")

    if mode == "view":
        kb = get_schedule_view_kb(i18n)
    else:
        kb = get_schedule_edit_kb(rows=rows, i18n=i18n)

    if edit:
        await message.edit_text(text=text, reply_markup=kb)
    else:
        await message.answer(text=text, reply_markup=kb)


@schedule_router.callback_query(
    ScheduleNavCallback.filter(F.action == "close"),
)
async def process_schedule_close(
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


@schedule_router.callback_query(ScheduleNavCallback.filter(F.action == "edit"))
async def process_schedule_edit(
        callback: CallbackQuery,
        repos: Repositories,
        user: User,
        i18n: dict[str, str],
) -> None:
    await show_schedule_list(
        message=callback.message,
        repos=repos,
        user=user,
        i18n=i18n,
        mode="edit",
        edit=True,
    )
    await callback.answer()


@schedule_router.callback_query(ScheduleNavCallback.filter(F.action == "view"))
async def process_schedule_view(
        callback: CallbackQuery,
        repos: Repositories,
        user: User,
        i18n: dict[str, str],
) -> None:
    """Back from edit → read-only view."""
    await show_schedule_list(
        message=callback.message,
        repos=repos,
        user=user,
        i18n=i18n,
        mode="view",
        edit=True,
    )
    await callback.answer()


@schedule_router.callback_query(ScheduleDeleteCallback.filter())
async def process_schedule_delete(
        callback: CallbackQuery,
        callback_data: ScheduleDeleteCallback,
        repos: Repositories,
        user: User,
        i18n: dict[str, str],
) -> None:
    row = await repos.working_hours.get(
        working_hours_id=callback_data.working_hours_id,
    )
    if row is None or row.master_user_id != user.user_id:
        await callback.answer(
            text=i18n.get("schedule_delete_not_found"),
            show_alert=True,
        )
        return

    item = format_interval_line(row, i18n).lstrip("• ").strip()
    await callback.message.edit_text(
        text=i18n.get("schedule_confirm_delete").format(item=item),
        reply_markup=get_schedule_confirm_delete_kb(
            working_hours_id=row.id,
            i18n=i18n,
        ),
    )
    await callback.answer()


@schedule_router.callback_query(
    ScheduleConfirmCallback.filter(F.action == "yes")
)
async def process_schedule_delete_yes(
        callback: CallbackQuery,
        callback_data: ScheduleConfirmCallback,
        repos: Repositories,
        user: User,
        i18n: dict[str, str],
) -> None:
    deleted = await repos.working_hours.delete(
        working_hours_id=callback_data.working_hours_id,
        master_user_id=user.user_id,
    )
    if not deleted:
        await callback.answer(
            text=i18n.get("schedule_delete_not_found"),
            show_alert=True,
        )
        return
    await callback.answer(text=i18n.get("schedule_deleted"))
    await show_schedule_list(
        message=callback.message,
        repos=repos,
        user=user,
        i18n=i18n,
        mode="edit",
        edit=True,
    )


@schedule_router.callback_query(
    ScheduleConfirmCallback.filter(F.action == "no")
)
async def process_schedule_delete_no(
        callback: CallbackQuery,
        repos: Repositories,
        user: User,
        i18n: dict[str, str],
) -> None:
    await show_schedule_list(
        message=callback.message,
        repos=repos,
        user=user,
        i18n=i18n,
        mode="edit",
        edit=True,
    )
    await callback.answer()


@schedule_router.callback_query(ScheduleNavCallback.filter(F.action == "add"))
async def process_schedule_add(
        callback: CallbackQuery,
        state: FSMContext,
        i18n: dict[str, str],
) -> None:
    await clear_state_keep_hub(state)
    await state.set_state(ScheduleSG.starts_time)
    await callback.message.edit_text(
        text=i18n.get("schedule_enter_starts"),
        reply_markup=get_schedule_cancel_kb(i18n),
    )
    await callback.answer()


@schedule_router.message(StateFilter(ScheduleSG.starts_time))
async def process_schedule_starts(
        message: Message,
        state: FSMContext,
        i18n: dict[str, str],
) -> None:
    starts = _parse_time(message.text or "")
    if starts is None:
        await message.answer(
            text=i18n.get("schedule_invalid_time"),
            reply_markup=get_schedule_cancel_kb(i18n),
        )
        return
    await state.update_data(starts_time=starts.isoformat())
    await state.set_state(ScheduleSG.ends_time)
    await message.answer(
        text=i18n.get("schedule_enter_ends"),
        reply_markup=get_schedule_cancel_kb(i18n),
    )


@schedule_router.message(StateFilter(ScheduleSG.ends_time))
async def process_schedule_ends(
        message: Message,
        state: FSMContext,
        i18n: dict[str, str],
) -> None:
    ends = _parse_time(message.text or "")
    if ends is None:
        await message.answer(
            text=i18n.get("schedule_invalid_time"),
            reply_markup=get_schedule_cancel_kb(i18n),
        )
        return

    data = await state.get_data()
    starts = time.fromisoformat(data["starts_time"])
    if ends <= starts:
        await message.answer(
            text=i18n.get("schedule_invalid_range"),
            reply_markup=get_schedule_cancel_kb(i18n),
        )
        return

    await state.update_data(ends_time=ends.isoformat(), weekdays=[])
    await state.set_state(ScheduleSG.weekdays)
    await message.answer(
        text=i18n.get("schedule_choose_weekdays").format(
            starts=_format_hm(starts),
            ends=_format_hm(ends),
        ),
        reply_markup=get_weekdays_kb(selected=set(), i18n=i18n),
    )


@schedule_router.callback_query(
    ScheduleWeekdayCallback.filter(),
    StateFilter(ScheduleSG.weekdays),
)
async def process_schedule_weekday_toggle(
        callback: CallbackQuery,
        callback_data: ScheduleWeekdayCallback,
        state: FSMContext,
        i18n: dict[str, str],
) -> None:
    data = await state.get_data()
    selected = set(data.get("weekdays") or [])
    day = callback_data.weekday
    if day in selected:
        selected.remove(day)
    else:
        selected.add(day)
    await state.update_data(weekdays=sorted(selected))

    starts = time.fromisoformat(data["starts_time"])
    ends = time.fromisoformat(data["ends_time"])
    await callback.message.edit_text(
        text=i18n.get("schedule_choose_weekdays").format(
            starts=_format_hm(starts),
            ends=_format_hm(ends),
        ),
        reply_markup=get_weekdays_kb(selected=selected, i18n=i18n),
    )
    await callback.answer()


@schedule_router.callback_query(
    ScheduleNavCallback.filter(F.action == "save"),
    StateFilter(ScheduleSG.weekdays),
)
async def process_schedule_save(
        callback: CallbackQuery,
        state: FSMContext,
        repos: Repositories,
        user: User,
        i18n: dict[str, str],
) -> None:
    data = await state.get_data()
    selected = set(data.get("weekdays") or [])
    if not selected:
        await callback.answer(
            text=i18n.get("schedule_need_weekday"),
            show_alert=True,
        )
        return

    starts = time.fromisoformat(data["starts_time"])
    ends = time.fromisoformat(data["ends_time"])
    for weekday in sorted(selected):
        await repos.working_hours.add(
            master_user_id=user.user_id,
            weekday=weekday,
            starts_time=starts,
            ends_time=ends,
        )

    await clear_state_keep_hub(state)
    await callback.answer(
        text=i18n.get("schedule_add_ok").format(
            starts=_format_hm(starts),
            ends=_format_hm(ends),
            days=_weekdays_label(selected, i18n),
        ),
    )
    await show_schedule_list(
        message=callback.message,
        repos=repos,
        user=user,
        i18n=i18n,
        mode="edit",
        edit=True,
    )


@schedule_router.callback_query(
    ScheduleNavCallback.filter(F.action == "back"),
    StateFilter(ScheduleSG.weekdays),
)
async def process_schedule_back(
        callback: CallbackQuery,
        state: FSMContext,
        i18n: dict[str, str],
) -> None:
    await state.set_state(ScheduleSG.ends_time)
    await callback.message.edit_text(
        text=i18n.get("schedule_enter_ends"),
        reply_markup=get_schedule_cancel_kb(i18n),
    )
    await callback.answer()


@schedule_router.callback_query(
    ScheduleNavCallback.filter(F.action == "cancel"),
    StateFilter(ScheduleSG),
)
async def process_schedule_cancel_cb(
        callback: CallbackQuery,
        state: FSMContext,
        repos: Repositories,
        user: User,
        i18n: dict[str, str],
) -> None:
    await clear_state_keep_hub(state)
    await show_schedule_list(
        message=callback.message,
        repos=repos,
        user=user,
        i18n=i18n,
        mode="edit",
        edit=True,
    )
    await callback.answer()


async def _hub_working_hours(
        *,
        message: Message,
        user: User,
        i18n: dict[str, str],
        state: FSMContext,
        repos: Repositories | None = None,
        **_,
) -> None:
    if user.role != UserRole.MASTER or repos is None:
        return
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
        mode="view",
        edit=True,
    )


register("working_hours", _hub_working_hours)
