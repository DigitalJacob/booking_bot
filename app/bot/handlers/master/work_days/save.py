from datetime import date, time

from aiogram import F
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.bot.handlers.master.work_days.calendar import show_work_days_calendar
from app.bot.handlers.master.work_days.common import (
    MAX_WARN_LINES,
    day_sets,
    format_day_list,
    format_hm,
)
from app.bot.handlers.master.work_days.months import show_work_days_months
from app.bot.handlers.master.work_days.router import work_days_router
from app.bot.keyboards.hub import get_hub_dismiss_kb
from app.bot.keyboards.work_days import (
    WorkDaysNavCallback,
    get_work_days_cancel_kb,
    get_work_days_confirm_kb,
    get_work_days_warn_kb,
    month_label,
)
from app.bot.states.states import WorkDaysSG
from app.bot.utils.dates import parse_time
from app.bot.utils.format import appointment_client_contact, format_dt
from app.bot.utils.hub_nav import clear_state_keep_hub, show_hub_prompt
from app.bot.utils.telegram import delete_user_input
from app.domain.models import Appointment, User
from app.domain.services.schedule_conflicts import ScheduleConflictsService
from app.infrastructure.database.repositories import Repositories


async def _show_starts_prompt(
    *,
    message: Message,
    state: FSMContext,
    i18n: dict[str, str],
) -> None:
    await state.set_state(WorkDaysSG.starts_time)
    await show_hub_prompt(
        message=message,
        state=state,
        text=i18n.get("work_days_enter_starts"),
        reply_markup=get_work_days_cancel_kb(i18n),
    )


async def _show_ends_prompt(
    *,
    message: Message,
    state: FSMContext,
    i18n: dict[str, str],
) -> None:
    await state.set_state(WorkDaysSG.ends_time)
    await show_hub_prompt(
        message=message,
        state=state,
        text=i18n.get("work_days_enter_ends"),
        reply_markup=get_work_days_cancel_kb(i18n),
    )


async def _show_confirm(
    *,
    message: Message,
    state: FSMContext,
    i18n: dict[str, str],
    mode: str | None = None,
) -> None:
    """mode: clear | off | set. If None, infer from current selection."""
    data = await state.get_data()
    year = int(data["wd_year"])
    month = int(data["wd_month"])
    days = data.get("wd_days") or []
    _, _, removed, added = day_sets(data)
    await state.set_state(WorkDaysSG.confirming)

    if mode is None:
        if not days:
            mode = "clear"
        elif removed and not added:
            mode = "off"
        else:
            mode = "set"

    if mode == "clear":
        text = i18n.get("work_days_confirm_clear").format(
            month=month_label(year, month, i18n),
        )
    elif mode == "off":
        text = i18n.get("work_days_confirm_off").format(
            dates=format_day_list(removed),
        )
    else:
        starts = time.fromisoformat(data["wd_starts"])
        ends = time.fromisoformat(data["wd_ends"])
        text = i18n.get("work_days_confirm").format(
            dates=format_day_list(added),
            starts=format_hm(starts),
            ends=format_hm(ends),
        )

    await state.update_data(wd_confirm_mode=mode)
    await show_hub_prompt(
        message=message,
        state=state,
        text=text,
        reply_markup=get_work_days_confirm_kb(i18n),
    )


async def _warn_bookings_text(
    *,
    repos: Repositories,
    appointments: list[Appointment],
    i18n: dict[str, str],
    bot_timezone: str,
) -> str:
    lines: list[str] = []
    for appointment in appointments[:MAX_WARN_LINES]:
        name, _ = await appointment_client_contact(repos, appointment)
        lines.append(
            i18n.get("work_days_warn_item").format(
                when=format_dt(appointment.starts_at, bot_timezone),
                client=name,
            )
        )
    extra = len(appointments) - MAX_WARN_LINES
    if extra > 0:
        lines.append(i18n.get("work_days_warn_more").format(n=extra))
    return i18n.get("work_days_warn_header").format(list="\n".join(lines))


async def _show_warn_bookings(
    *,
    message: Message,
    state: FSMContext,
    repos: Repositories,
    appointments: list[Appointment],
    i18n: dict[str, str],
    bot_timezone: str,
) -> None:
    text = await _warn_bookings_text(
        repos=repos,
        appointments=appointments,
        i18n=i18n,
        bot_timezone=bot_timezone,
    )
    await state.set_state(WorkDaysSG.warn_bookings)
    await show_hub_prompt(
        message=message,
        state=state,
        text=text,
        reply_markup=get_work_days_warn_kb(i18n),
    )


async def _apply_work_days_save(
    *,
    message: Message,
    state: FSMContext,
    repos: Repositories,
    user: User,
    i18n: dict[str, str],
    bot_timezone: str,
) -> None:
    data = await state.get_data()
    year = int(data["wd_year"])
    month = int(data["wd_month"])
    _, _, removed, added = day_sets(data)
    removed_dates = [date.fromisoformat(value) for value in removed]
    added_dates = [date.fromisoformat(value) for value in added]
    confirm_mode = data.get("wd_confirm_mode") or (
        "clear" if not (data.get("wd_days") or []) else "set"
    )

    if confirm_mode == "clear":
        await repos.work_dates.replace_month(
            master_user_id=user.user_id,
            year=year,
            month=month,
            work_dates=[],
        )
        saved_text = i18n.get("work_days_cleared").format(
            month=month_label(year, month, i18n),
        )
    elif confirm_mode == "off":
        await repos.work_dates.delete_dates(
            master_user_id=user.user_id,
            work_dates=removed_dates,
        )
        saved_text = i18n.get("work_days_off_saved").format(
            dates=format_day_list(removed),
        )
    else:
        if removed_dates:
            await repos.work_dates.delete_dates(
                master_user_id=user.user_id,
                work_dates=removed_dates,
            )
        starts = time.fromisoformat(data["wd_starts"])
        ends = time.fromisoformat(data["wd_ends"])
        await repos.work_dates.upsert_dates(
            master_user_id=user.user_id,
            work_dates=added_dates,
            starts_time=starts,
            ends_time=ends,
        )
        saved_text = i18n.get("work_days_saved").format(
            dates=format_day_list(added),
            starts=format_hm(starts),
            ends=format_hm(ends),
        )

    await clear_state_keep_hub(state)
    await state.update_data(
        hub_screen="work_days",
        hub_back="schedule",
        list_return="schedule",
    )
    await show_work_days_months(
        message=message,
        state=state,
        repos=repos,
        user=user,
        i18n=i18n,
        bot_timezone=bot_timezone,
    )
    await message.answer(
        text=saved_text,
        reply_markup=get_hub_dismiss_kb(i18n),
    )


@work_days_router.callback_query(
    WorkDaysNavCallback.filter(F.action == "next"),
    StateFilter(WorkDaysSG.choosing_days),
)
async def process_work_days_next(
    callback: CallbackQuery,
    state: FSMContext,
    i18n: dict[str, str],
) -> None:
    data = await state.get_data()
    current, _initial, removed, added = day_sets(data)

    if not current:
        await _show_confirm(
            message=callback.message,
            state=state,
            i18n=i18n,
            mode="clear",
        )
        await callback.answer()
        return

    if not removed and not added:
        await callback.answer(
            text=i18n.get("work_days_no_changes"),
            show_alert=True,
        )
        return

    # Only days off (no new open days) → delete those days only.
    if removed and not added:
        await _show_confirm(
            message=callback.message,
            state=state,
            i18n=i18n,
            mode="off",
        )
        await callback.answer()
        return

    # New open day(s) → ask hours for those days only (upsert later).
    await _show_starts_prompt(
        message=callback.message,
        state=state,
        i18n=i18n,
    )
    await callback.answer()


@work_days_router.message(StateFilter(WorkDaysSG.starts_time))
async def process_work_days_starts(
    message: Message,
    state: FSMContext,
    i18n: dict[str, str],
) -> None:
    starts = parse_time(message.text or "")
    await delete_user_input(message)
    if starts is None:
        await show_hub_prompt(
            message=message,
            state=state,
            text=i18n.get("schedule_invalid_time"),
            reply_markup=get_work_days_cancel_kb(i18n),
        )
        return
    await state.update_data(wd_starts=starts.isoformat())
    await _show_ends_prompt(message=message, state=state, i18n=i18n)


@work_days_router.message(StateFilter(WorkDaysSG.ends_time))
async def process_work_days_ends(
    message: Message,
    state: FSMContext,
    i18n: dict[str, str],
) -> None:
    ends = parse_time(message.text or "")
    await delete_user_input(message)
    if ends is None:
        await show_hub_prompt(
            message=message,
            state=state,
            text=i18n.get("schedule_invalid_time"),
            reply_markup=get_work_days_cancel_kb(i18n),
        )
        return

    data = await state.get_data()
    starts = time.fromisoformat(data["wd_starts"])
    if ends <= starts:
        await show_hub_prompt(
            message=message,
            state=state,
            text=i18n.get("schedule_invalid_range"),
            reply_markup=get_work_days_cancel_kb(i18n),
        )
        return

    await state.update_data(wd_ends=ends.isoformat())
    await _show_confirm(message=message, state=state, i18n=i18n)


@work_days_router.callback_query(
    WorkDaysNavCallback.filter(F.action == "confirm_no"),
    StateFilter(WorkDaysSG.confirming, WorkDaysSG.warn_bookings),
)
async def process_work_days_confirm_no(
    callback: CallbackQuery,
    state: FSMContext,
    i18n: dict[str, str],
) -> None:
    await show_work_days_calendar(
        message=callback.message,
        state=state,
        i18n=i18n,
    )
    await callback.answer()


@work_days_router.callback_query(
    WorkDaysNavCallback.filter(F.action == "confirm_yes"),
    StateFilter(WorkDaysSG.confirming),
)
async def process_work_days_confirm_yes(
    callback: CallbackQuery,
    state: FSMContext,
    repos: Repositories,
    user: User,
    i18n: dict[str, str],
    bot_timezone: str,
) -> None:
    data = await state.get_data()
    _, _, removed, _ = day_sets(data)
    removed_dates = {date.fromisoformat(value) for value in removed}
    conflicting = await ScheduleConflictsService(repos).active_on_local_days(
        master_user_id=user.user_id,
        days=removed_dates,
        timezone=bot_timezone,
    )
    if conflicting:
        await _show_warn_bookings(
            message=callback.message,
            state=state,
            repos=repos,
            appointments=conflicting,
            i18n=i18n,
            bot_timezone=bot_timezone,
        )
        await callback.answer()
        return

    await _apply_work_days_save(
        message=callback.message,
        state=state,
        repos=repos,
        user=user,
        i18n=i18n,
        bot_timezone=bot_timezone,
    )
    await callback.answer()


@work_days_router.callback_query(
    WorkDaysNavCallback.filter(F.action == "save_anyway"),
    StateFilter(WorkDaysSG.warn_bookings),
)
async def process_work_days_save_anyway(
    callback: CallbackQuery,
    state: FSMContext,
    repos: Repositories,
    user: User,
    i18n: dict[str, str],
    bot_timezone: str,
) -> None:
    await _apply_work_days_save(
        message=callback.message,
        state=state,
        repos=repos,
        user=user,
        i18n=i18n,
        bot_timezone=bot_timezone,
    )
    await callback.answer()
