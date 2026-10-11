from __future__ import annotations

from datetime import date, datetime, time, timedelta

from aiogram import F
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.bot.handlers.master.time_off.common import (
    MAX_WARN_LINES,
    PENDING_ENDS_KEY,
    PENDING_KIND_KEY,
    PENDING_STARTS_KEY,
    PENDING_WHEN_KEY,
    format_day_range,
    format_hours_when,
    is_breaks_mode,
    parse_date,
    show_time_off_prompt,
    today_local,
)
from app.bot.handlers.master.time_off.list import show_time_off_list
from app.bot.handlers.master.time_off.router import time_off_router
from app.bot.keyboards.hub import get_hub_dismiss_kb
from app.bot.keyboards.time_off import (
    TimeOffNavCallback,
    get_time_off_kind_kb,
    get_time_off_warn_kb,
)
from app.bot.states.states import TimeOffSG
from app.bot.utils.dates import parse_time
from app.bot.utils.format import (
    client_contact,
    combine_local,
    format_dt,
    get_zone,
)
from app.bot.utils.hub_nav import clear_state_keep_hub
from app.bot.utils.telegram import delete_user_input
from app.domain.models import Appointment, User
from app.domain.services.schedule_conflicts import ScheduleConflictsService
from app.infrastructure.database.repositories import Repositories


async def _finish_time_off_add(
    *,
    message: Message,
    state: FSMContext,
    repos: Repositories,
    user: User,
    i18n: dict[str, str],
    bot_timezone: str,
    when: str,
    schedule_mode: str = "weekly",
) -> None:
    await clear_state_keep_hub(state)
    await show_time_off_list(
        message=message,
        repos=repos,
        user=user,
        i18n=i18n,
        bot_timezone=bot_timezone,
        edit=False,
        state=state,
        prefer_sticky=True,
        schedule_mode=schedule_mode,
    )
    ok_key = "time_off_breaks_add_ok" if is_breaks_mode(schedule_mode) else "time_off_add_ok"
    await message.answer(
        text=i18n.get(ok_key).format(when=when),
        reply_markup=get_hub_dismiss_kb(i18n),
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
        client = await repos.users.get_user_by_id(
            user_id=appointment.client_user_id,
        )
        name, _ = client_contact(client)
        lines.append(
            i18n.get("time_off_warn_item").format(
                when=format_dt(appointment.starts_at, bot_timezone),
                client=name,
            )
        )
    extra = len(appointments) - MAX_WARN_LINES
    if extra > 0:
        lines.append(i18n.get("time_off_warn_more").format(n=extra))
    return i18n.get("time_off_warn_header").format(list="\n".join(lines))


async def _show_warn_bookings(
    *,
    message: Message,
    state: FSMContext,
    repos: Repositories,
    appointments: list[Appointment],
    i18n: dict[str, str],
    bot_timezone: str,
    starts_at: datetime,
    ends_at: datetime,
    when: str,
    kind: str,
) -> None:
    await state.update_data(
        {
            PENDING_STARTS_KEY: starts_at.isoformat(),
            PENDING_ENDS_KEY: ends_at.isoformat(),
            PENDING_WHEN_KEY: when,
            PENDING_KIND_KEY: kind,
        }
    )
    text = await _warn_bookings_text(
        repos=repos,
        appointments=appointments,
        i18n=i18n,
        bot_timezone=bot_timezone,
    )
    await state.set_state(TimeOffSG.warn_bookings)
    await show_time_off_prompt(
        message=message,
        state=state,
        text=text,
        i18n=i18n,
        reply_markup=get_time_off_warn_kb(i18n),
    )


async def _apply_pending_time_off(
    *,
    message: Message,
    state: FSMContext,
    repos: Repositories,
    user: User,
    i18n: dict[str, str],
    bot_timezone: str,
    schedule_mode: str,
) -> None:
    data = await state.get_data()
    starts_raw = data.get(PENDING_STARTS_KEY)
    ends_raw = data.get(PENDING_ENDS_KEY)
    when = data.get(PENDING_WHEN_KEY)
    if not starts_raw or not ends_raw or not when:
        await clear_state_keep_hub(state)
        await show_time_off_list(
            message=message,
            repos=repos,
            user=user,
            i18n=i18n,
            bot_timezone=bot_timezone,
            edit=True,
            state=state,
            prefer_sticky=True,
            schedule_mode=schedule_mode,
        )
        return

    starts_at = datetime.fromisoformat(str(starts_raw))
    ends_at = datetime.fromisoformat(str(ends_raw))
    await repos.time_off.add(
        master_user_id=user.user_id,
        starts_at=starts_at,
        ends_at=ends_at,
        note=None,
    )
    await _finish_time_off_add(
        message=message,
        state=state,
        repos=repos,
        user=user,
        i18n=i18n,
        bot_timezone=bot_timezone,
        when=str(when),
        schedule_mode=schedule_mode,
    )


async def _save_time_off_or_warn(
    *,
    message: Message,
    state: FSMContext,
    repos: Repositories,
    user: User,
    i18n: dict[str, str],
    bot_timezone: str,
    schedule_mode: str,
    starts_at: datetime,
    ends_at: datetime,
    when: str,
    kind: str,
) -> None:
    conflicting = await ScheduleConflictsService(repos).active_overlapping(
        master_user_id=user.user_id,
        starts_at=starts_at,
        ends_at=ends_at,
    )
    if conflicting:
        await _show_warn_bookings(
            message=message,
            state=state,
            repos=repos,
            appointments=conflicting,
            i18n=i18n,
            bot_timezone=bot_timezone,
            starts_at=starts_at,
            ends_at=ends_at,
            when=when,
            kind=kind,
        )
        return

    await repos.time_off.add(
        master_user_id=user.user_id,
        starts_at=starts_at,
        ends_at=ends_at,
        note=None,
    )
    await _finish_time_off_add(
        message=message,
        state=state,
        repos=repos,
        user=user,
        i18n=i18n,
        bot_timezone=bot_timezone,
        when=when,
        schedule_mode=schedule_mode,
    )


async def _start_hours_add(
    *,
    message: Message,
    state: FSMContext,
    i18n: dict[str, str],
    bot_timezone: str,
) -> None:
    """Weekly: typed DD.MM.YYYY for hours-in-one-day."""
    await state.set_state(TimeOffSG.hours_day)
    example = today_local(bot_timezone).strftime("%d.%m.%Y")
    await show_time_off_prompt(
        message=message,
        state=state,
        text=i18n.get("time_off_enter_hours_day").format(example=example),
        i18n=i18n,
    )


@time_off_router.callback_query(TimeOffNavCallback.filter(F.action == "add"))
async def process_time_off_add(
    callback: CallbackQuery,
    state: FSMContext,
    repos: Repositories,
    user: User,
    i18n: dict[str, str],
    bot_timezone: str,
    schedule_mode: str,
) -> None:
    await clear_state_keep_hub(state)
    if is_breaks_mode(schedule_mode):
        # Monthly: pick an open work day on the calendar, then hours.
        from app.bot.handlers.master.time_off.breaks_calendar import (
            show_break_day_calendar,
        )

        await show_break_day_calendar(
            message=callback.message,
            state=state,
            repos=repos,
            user=user,
            i18n=i18n,
            bot_timezone=bot_timezone,
        )
        await callback.answer()
        return

    await state.set_state(TimeOffSG.choosing_kind)
    await show_time_off_prompt(
        message=callback.message,
        state=state,
        text=i18n.get("time_off_choose_kind"),
        i18n=i18n,
        reply_markup=get_time_off_kind_kb(i18n),
    )
    await callback.answer()


@time_off_router.callback_query(
    TimeOffNavCallback.filter(F.action == "days"),
    StateFilter(TimeOffSG.choosing_kind),
)
async def process_time_off_kind_days(
    callback: CallbackQuery,
    state: FSMContext,
    i18n: dict[str, str],
    bot_timezone: str,
) -> None:
    await state.set_state(TimeOffSG.starts_date)
    example = today_local(bot_timezone).strftime("%d.%m.%Y")
    await show_time_off_prompt(
        message=callback.message,
        state=state,
        text=i18n.get("time_off_enter_starts").format(example=example),
        i18n=i18n,
    )
    await callback.answer()


@time_off_router.callback_query(
    TimeOffNavCallback.filter(F.action == "hours"),
    StateFilter(TimeOffSG.choosing_kind),
)
async def process_time_off_kind_hours(
    callback: CallbackQuery,
    state: FSMContext,
    i18n: dict[str, str],
    bot_timezone: str,
) -> None:
    await _start_hours_add(
        message=callback.message,
        state=state,
        i18n=i18n,
        bot_timezone=bot_timezone,
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
    schedule_mode: str,
) -> None:
    await clear_state_keep_hub(state)
    await show_time_off_list(
        message=callback.message,
        repos=repos,
        user=user,
        i18n=i18n,
        bot_timezone=bot_timezone,
        edit=True,
        state=state,
        prefer_sticky=True,
        schedule_mode=schedule_mode,
    )
    await callback.answer()


@time_off_router.message(StateFilter(TimeOffSG.starts_date))
async def process_time_off_starts(
    message: Message,
    state: FSMContext,
    i18n: dict[str, str],
    bot_timezone: str,
) -> None:
    starts = parse_date(message.text or "")
    await delete_user_input(message)
    if starts is None:
        await message.answer(text=i18n.get("time_off_invalid_date"))
        return

    await state.update_data(starts_date=starts.isoformat())
    await state.set_state(TimeOffSG.ends_date)
    example = max(starts, today_local(bot_timezone)).strftime("%d.%m.%Y")
    await show_time_off_prompt(
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
    schedule_mode: str,
) -> None:
    ends = parse_date(message.text or "")
    await delete_user_input(message)
    if ends is None:
        await message.answer(text=i18n.get("time_off_invalid_date"))
        return

    data = await state.get_data()
    starts = date.fromisoformat(data["starts_date"])
    if ends < starts:
        await message.answer(text=i18n.get("time_off_invalid_range"))
        return

    if ends < today_local(bot_timezone):
        await message.answer(text=i18n.get("time_off_invalid_past"))
        return

    starts_at = combine_local(starts, time(0, 0), bot_timezone)
    ends_at = combine_local(ends + timedelta(days=1), time(0, 0), bot_timezone)

    await _save_time_off_or_warn(
        message=message,
        state=state,
        repos=repos,
        user=user,
        i18n=i18n,
        bot_timezone=bot_timezone,
        schedule_mode=schedule_mode,
        starts_at=starts_at,
        ends_at=ends_at,
        when=format_day_range(starts, ends),
        kind="days",
    )


@time_off_router.message(StateFilter(TimeOffSG.hours_day))
async def process_time_off_hours_day(
    message: Message,
    state: FSMContext,
    i18n: dict[str, str],
    bot_timezone: str,
) -> None:
    day = parse_date(message.text or "")
    await delete_user_input(message)
    if day is None:
        await message.answer(text=i18n.get("time_off_invalid_date"))
        return

    if day < today_local(bot_timezone):
        await message.answer(text=i18n.get("time_off_invalid_past"))
        return

    await state.update_data(hours_day=day.isoformat())
    await state.set_state(TimeOffSG.starts_time)
    await show_time_off_prompt(
        message=message,
        state=state,
        text=i18n.get("time_off_enter_hours_starts"),
        i18n=i18n,
    )


@time_off_router.message(StateFilter(TimeOffSG.starts_time))
async def process_time_off_hours_starts(
    message: Message,
    state: FSMContext,
    i18n: dict[str, str],
) -> None:
    starts = parse_time(message.text or "")
    await delete_user_input(message)
    if starts is None:
        await message.answer(text=i18n.get("time_off_invalid_time"))
        return

    await state.update_data(starts_time=starts.isoformat())
    await state.set_state(TimeOffSG.ends_time)
    await show_time_off_prompt(
        message=message,
        state=state,
        text=i18n.get("time_off_enter_hours_ends"),
        i18n=i18n,
    )


@time_off_router.message(StateFilter(TimeOffSG.ends_time))
async def process_time_off_hours_ends(
    message: Message,
    state: FSMContext,
    repos: Repositories,
    user: User,
    i18n: dict[str, str],
    bot_timezone: str,
    schedule_mode: str,
) -> None:
    ends = parse_time(message.text or "")
    await delete_user_input(message)
    if ends is None:
        await message.answer(text=i18n.get("time_off_invalid_time"))
        return

    data = await state.get_data()
    day = date.fromisoformat(data["hours_day"])
    starts = time.fromisoformat(data["starts_time"])
    if ends <= starts:
        await message.answer(text=i18n.get("time_off_invalid_time_range"))
        return

    starts_at = combine_local(day, starts, bot_timezone)
    ends_at = combine_local(day, ends, bot_timezone)
    now_local = datetime.now(get_zone(bot_timezone))
    if ends_at <= now_local:
        await message.answer(text=i18n.get("time_off_invalid_hours_past"))
        return

    await _save_time_off_or_warn(
        message=message,
        state=state,
        repos=repos,
        user=user,
        i18n=i18n,
        bot_timezone=bot_timezone,
        schedule_mode=schedule_mode,
        starts_at=starts_at,
        ends_at=ends_at,
        when=format_hours_when(day, starts, ends),
        kind="hours",
    )


@time_off_router.callback_query(
    TimeOffNavCallback.filter(F.action == "save_anyway"),
    StateFilter(TimeOffSG.warn_bookings),
)
async def process_time_off_save_anyway(
    callback: CallbackQuery,
    state: FSMContext,
    repos: Repositories,
    user: User,
    i18n: dict[str, str],
    bot_timezone: str,
    schedule_mode: str,
) -> None:
    await _apply_pending_time_off(
        message=callback.message,
        state=state,
        repos=repos,
        user=user,
        i18n=i18n,
        bot_timezone=bot_timezone,
        schedule_mode=schedule_mode,
    )
    await callback.answer()


@time_off_router.callback_query(
    TimeOffNavCallback.filter(F.action == "warn_back"),
    StateFilter(TimeOffSG.warn_bookings),
)
async def process_time_off_warn_back(
    callback: CallbackQuery,
    state: FSMContext,
    i18n: dict[str, str],
    bot_timezone: str,
) -> None:
    data = await state.get_data()
    kind = data.get(PENDING_KIND_KEY)
    if kind == "hours":
        await state.set_state(TimeOffSG.ends_time)
        await show_time_off_prompt(
            message=callback.message,
            state=state,
            text=i18n.get("time_off_enter_hours_ends"),
            i18n=i18n,
        )
    else:
        await state.set_state(TimeOffSG.ends_date)
        example = today_local(bot_timezone).strftime("%d.%m.%Y")
        starts_raw = data.get("starts_date")
        if starts_raw:
            starts = date.fromisoformat(str(starts_raw))
            example = max(starts, today_local(bot_timezone)).strftime("%d.%m.%Y")
        await show_time_off_prompt(
            message=callback.message,
            state=state,
            text=i18n.get("time_off_enter_ends").format(example=example),
            i18n=i18n,
        )
    await callback.answer()
