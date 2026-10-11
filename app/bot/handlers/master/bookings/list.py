from __future__ import annotations

from datetime import date, time, timedelta

from aiogram import F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message

from app.bot.handlers.common.hub import return_from_list
from app.bot.handlers.master.bookings.common import (
    DAY_KEY,
    MONTH_KEY,
    WEEK_START_KEY,
    active_only,
    bookings_back_to,
    counts_by_local_day,
    day_label,
    load_month_active,
    load_week_active,
    parse_iso_date,
    truncate_button,
    week_range_label,
)
from app.bot.handlers.master.bookings.router import bookings_router
from app.bot.keyboards.bookings import (
    MasterAppointmentCallback,
    MasterBookingsPadCallback,
    get_master_bookings_day_kb,
    get_master_bookings_month_kb,
    get_master_bookings_week_kb,
)
from app.bot.keyboards.work_days import month_label
from app.bot.utils.dates import format_year_month, parse_year_month, shift_month
from app.bot.utils.format import (
    combine_local,
    i18n_plural,
    local_month_bounds,
    local_week_bounds,
    status_label,
    to_local,
)
from app.domain.models import User
from app.infrastructure.database.repositories import Repositories


async def show_master_bookings_week(
    *,
    message: Message,
    state: FSMContext,
    repos: Repositories,
    user: User,
    i18n: dict[str, str],
    bot_timezone: str,
    edit: bool,
) -> None:
    data = await state.get_data()
    week_start = parse_iso_date(data.get(WEEK_START_KEY))
    week_start, active, is_current_week = await load_week_active(
        repos=repos,
        user=user,
        bot_timezone=bot_timezone,
        week_start=week_start,
    )
    await state.update_data(
        {
            WEEK_START_KEY: week_start.isoformat(),
            MONTH_KEY: None,
            DAY_KEY: None,
        }
    )
    week_label = week_range_label(week_start)
    by_day = counts_by_local_day(
        appointments=active,
        bot_timezone=bot_timezone,
    )

    if not by_day:
        text = i18n.get("master_bookings_empty").format(week=week_label)
        day_buttons: list[tuple[date, str]] = []
    else:
        lines: list[str] = []
        day_buttons = []
        for day in sorted(by_day):
            count = by_day[day]
            day_text = day_label(day=day, i18n=i18n)
            lines.append(
                i18n_plural(
                    count,
                    i18n,
                    key_prefix="master_bookings_day_line",
                    day=day_text,
                )
            )
            day_buttons.append(
                (
                    day,
                    truncate_button(
                        i18n.get("master_bookings_day_button").format(
                            day=day_text,
                        )
                    ),
                )
            )
        total = i18n_plural(
            len(active),
            i18n,
            key_prefix="master_bookings_total",
        )
        text = (
            i18n.get("master_bookings_header").format(
                week=week_label,
                total=total,
            )
            + "\n\n"
            + "\n".join(lines)
        )

    kb = get_master_bookings_week_kb(
        day_buttons=day_buttons,
        i18n=i18n,
        is_current_week=is_current_week,
    )
    if edit:
        await message.edit_text(text=text, reply_markup=kb)
    else:
        await message.answer(text=text, reply_markup=kb)


async def show_master_bookings_month(
    *,
    message: Message,
    state: FSMContext,
    repos: Repositories,
    user: User,
    i18n: dict[str, str],
    bot_timezone: str,
    edit: bool,
) -> None:
    data = await state.get_data()
    parsed = parse_year_month(data.get(MONTH_KEY))
    year = parsed[0] if parsed else None
    month = parsed[1] if parsed else None
    year, month, active, is_current_month = await load_month_active(
        repos=repos,
        user=user,
        bot_timezone=bot_timezone,
        year=year,
        month=month,
    )
    await state.update_data(
        {
            MONTH_KEY: format_year_month(year, month),
            WEEK_START_KEY: None,
            DAY_KEY: None,
        }
    )
    month_text = month_label(year, month, i18n)
    by_day = counts_by_local_day(
        appointments=active,
        bot_timezone=bot_timezone,
    )
    busy_days = {day.day for day in by_day}

    if not by_day:
        text = i18n.get("master_bookings_month_empty").format(month=month_text)
    else:
        lines: list[str] = []
        for day in sorted(by_day):
            count = by_day[day]
            day_text = day_label(day=day, i18n=i18n)
            lines.append(
                i18n_plural(
                    count,
                    i18n,
                    key_prefix="master_bookings_day_line",
                    day=day_text,
                )
            )
        total = i18n_plural(
            len(active),
            i18n,
            key_prefix="master_bookings_total",
        )
        text = (
            i18n.get("master_bookings_month_header").format(
                month=month_text,
                total=total,
            )
            + "\n\n"
            + "\n".join(lines)
        )

    kb = get_master_bookings_month_kb(
        year=year,
        month=month,
        busy_days=busy_days,
        i18n=i18n,
        is_current_month=is_current_month,
    )
    if edit:
        await message.edit_text(text=text, reply_markup=kb)
    else:
        await message.answer(text=text, reply_markup=kb)


async def show_master_bookings_overview(
    *,
    message: Message,
    state: FSMContext,
    repos: Repositories,
    user: User,
    i18n: dict[str, str],
    bot_timezone: str,
    schedule_mode: str,
    edit: bool,
) -> None:
    if schedule_mode == "monthly":
        await show_master_bookings_month(
            message=message,
            state=state,
            repos=repos,
            user=user,
            i18n=i18n,
            bot_timezone=bot_timezone,
            edit=edit,
        )
        return
    await show_master_bookings_week(
        message=message,
        state=state,
        repos=repos,
        user=user,
        i18n=i18n,
        bot_timezone=bot_timezone,
        edit=edit,
    )


async def build_master_bookings_day(
    *,
    repos: Repositories,
    user: User,
    i18n: dict[str, str],
    bot_timezone: str,
    day: date,
    back_to: str = "week",
) -> tuple[str, InlineKeyboardMarkup]:
    day_start = combine_local(day, time.min, bot_timezone)
    day_end = day_start + timedelta(days=1)
    appointments = await repos.appointments.list_by_master(
        master_user_id=user.user_id,
        from_dt=day_start,
        to_dt=day_end,
    )
    active = active_only(appointments)
    day_text = day_label(day=day, i18n=i18n)

    if not active:
        return (
            i18n.get("master_bookings_day_empty").format(day=day_text),
            get_master_bookings_day_kb(
                appointments=[],
                labels={},
                i18n=i18n,
                back_to=back_to,
            ),
        )

    labels: dict[int, str] = {}
    lines: list[str] = []
    for appointment in active:
        service = await repos.services.get_service(
            service_id=appointment.service_id,
        )
        title = service.title if service else "?"
        local = to_local(appointment.starts_at, bot_timezone)
        slot_time = local.strftime("%H:%M")
        labels[appointment.id] = truncate_button(
            i18n.get("master_bookings_slot_button").format(
                time=slot_time,
                title=title,
            )
        )
        lines.append(
            i18n.get("master_bookings_day_item").format(
                time=slot_time,
                title=title,
                status=status_label(appointment.status, i18n),
            )
        )
    text = i18n.get("master_bookings_day_header").format(day=day_text) + "\n\n" + "\n".join(lines)
    kb = get_master_bookings_day_kb(
        appointments=active,
        labels=labels,
        i18n=i18n,
        back_to=back_to,
    )
    return text, kb


async def show_master_bookings_day(
    *,
    message: Message,
    state: FSMContext,
    repos: Repositories,
    user: User,
    i18n: dict[str, str],
    bot_timezone: str,
    day: date,
    edit: bool,
    schedule_mode: str = "weekly",
) -> None:
    updates: dict[str, str | None] = {DAY_KEY: day.isoformat()}
    if schedule_mode == "monthly":
        updates[MONTH_KEY] = format_year_month(day.year, day.month)
    else:
        updates[MONTH_KEY] = None
    await state.update_data(updates)
    text, kb = await build_master_bookings_day(
        repos=repos,
        user=user,
        i18n=i18n,
        bot_timezone=bot_timezone,
        day=day,
        back_to=bookings_back_to(schedule_mode),
    )
    if edit:
        await message.edit_text(text=text, reply_markup=kb)
    else:
        await message.answer(text=text, reply_markup=kb)


async def _set_week_start(
    *,
    state: FSMContext,
    bot_timezone: str,
    delta_weeks: int = 0,
    to_current: bool = False,
) -> None:
    if to_current:
        _, _, week_start = local_week_bounds(bot_timezone)
    else:
        data = await state.get_data()
        week_start = parse_iso_date(data.get(WEEK_START_KEY))
        _, _, week_start = local_week_bounds(
            bot_timezone,
            week_start=week_start,
        )
        week_start = week_start + timedelta(weeks=delta_weeks)
    await state.update_data(
        {
            WEEK_START_KEY: week_start.isoformat(),
            MONTH_KEY: None,
            DAY_KEY: None,
        }
    )


async def _set_month(
    *,
    state: FSMContext,
    bot_timezone: str,
    delta_months: int = 0,
    to_current: bool = False,
) -> None:
    if to_current:
        _, _, year, month = local_month_bounds(bot_timezone)
    else:
        data = await state.get_data()
        parsed = parse_year_month(data.get(MONTH_KEY))
        year = parsed[0] if parsed else None
        month = parsed[1] if parsed else None
        _, _, year, month = local_month_bounds(
            bot_timezone,
            year=year,
            month=month,
        )
        year, month = shift_month(year, month, delta_months)
    await state.update_data(
        {
            MONTH_KEY: format_year_month(year, month),
            WEEK_START_KEY: None,
            DAY_KEY: None,
        }
    )


@bookings_router.callback_query(MasterAppointmentCallback.filter(F.action == "open_day"))
async def process_open_day(
    callback: CallbackQuery,
    callback_data: MasterAppointmentCallback,
    state: FSMContext,
    repos: Repositories,
    user: User,
    i18n: dict[str, str],
    bot_timezone: str,
    schedule_mode: str,
) -> None:
    day = parse_iso_date(callback_data.day)
    if day is None:
        await callback.answer(
            text=i18n.get("master_action_failed"),
            show_alert=True,
        )
        return
    await show_master_bookings_day(
        message=callback.message,
        state=state,
        repos=repos,
        user=user,
        i18n=i18n,
        bot_timezone=bot_timezone,
        day=day,
        edit=True,
        schedule_mode=schedule_mode,
    )
    await callback.answer()


@bookings_router.callback_query(MasterAppointmentCallback.filter(F.action == "back"))
async def process_back(
    callback: CallbackQuery,
    state: FSMContext,
    repos: Repositories,
    user: User,
    i18n: dict[str, str],
    bot_timezone: str,
    schedule_mode: str,
) -> None:
    data = await state.get_data()
    day = parse_iso_date(data.get(DAY_KEY))
    if day is None:
        await show_master_bookings_overview(
            message=callback.message,
            state=state,
            repos=repos,
            user=user,
            i18n=i18n,
            bot_timezone=bot_timezone,
            schedule_mode=schedule_mode,
            edit=True,
        )
    else:
        await show_master_bookings_day(
            message=callback.message,
            state=state,
            repos=repos,
            user=user,
            i18n=i18n,
            bot_timezone=bot_timezone,
            day=day,
            edit=True,
            schedule_mode=schedule_mode,
        )
    await callback.answer()


@bookings_router.callback_query(
    MasterAppointmentCallback.filter(F.action == "back_week"),
)
async def process_back_week(
    callback: CallbackQuery,
    state: FSMContext,
    repos: Repositories,
    user: User,
    i18n: dict[str, str],
    bot_timezone: str,
) -> None:
    await show_master_bookings_week(
        message=callback.message,
        state=state,
        repos=repos,
        user=user,
        i18n=i18n,
        bot_timezone=bot_timezone,
        edit=True,
    )
    await callback.answer()


@bookings_router.callback_query(
    MasterAppointmentCallback.filter(F.action == "back_month"),
)
async def process_back_month(
    callback: CallbackQuery,
    state: FSMContext,
    repos: Repositories,
    user: User,
    i18n: dict[str, str],
    bot_timezone: str,
) -> None:
    await show_master_bookings_month(
        message=callback.message,
        state=state,
        repos=repos,
        user=user,
        i18n=i18n,
        bot_timezone=bot_timezone,
        edit=True,
    )
    await callback.answer()


@bookings_router.callback_query(
    MasterAppointmentCallback.filter(F.action == "week_prev"),
)
async def process_week_prev(
    callback: CallbackQuery,
    state: FSMContext,
    repos: Repositories,
    user: User,
    i18n: dict[str, str],
    bot_timezone: str,
) -> None:
    await _set_week_start(
        state=state,
        bot_timezone=bot_timezone,
        delta_weeks=-1,
    )
    await show_master_bookings_week(
        message=callback.message,
        state=state,
        repos=repos,
        user=user,
        i18n=i18n,
        bot_timezone=bot_timezone,
        edit=True,
    )
    await callback.answer()


@bookings_router.callback_query(
    MasterAppointmentCallback.filter(F.action == "week_next"),
)
async def process_week_next(
    callback: CallbackQuery,
    state: FSMContext,
    repos: Repositories,
    user: User,
    i18n: dict[str, str],
    bot_timezone: str,
) -> None:
    await _set_week_start(
        state=state,
        bot_timezone=bot_timezone,
        delta_weeks=1,
    )
    await show_master_bookings_week(
        message=callback.message,
        state=state,
        repos=repos,
        user=user,
        i18n=i18n,
        bot_timezone=bot_timezone,
        edit=True,
    )
    await callback.answer()


@bookings_router.callback_query(
    MasterAppointmentCallback.filter(F.action == "week_current"),
)
async def process_week_current(
    callback: CallbackQuery,
    state: FSMContext,
    repos: Repositories,
    user: User,
    i18n: dict[str, str],
    bot_timezone: str,
) -> None:
    await _set_week_start(
        state=state,
        bot_timezone=bot_timezone,
        to_current=True,
    )
    await show_master_bookings_week(
        message=callback.message,
        state=state,
        repos=repos,
        user=user,
        i18n=i18n,
        bot_timezone=bot_timezone,
        edit=True,
    )
    await callback.answer()


@bookings_router.callback_query(
    MasterAppointmentCallback.filter(F.action == "month_prev"),
)
async def process_month_prev(
    callback: CallbackQuery,
    state: FSMContext,
    repos: Repositories,
    user: User,
    i18n: dict[str, str],
    bot_timezone: str,
) -> None:
    await _set_month(
        state=state,
        bot_timezone=bot_timezone,
        delta_months=-1,
    )
    await show_master_bookings_month(
        message=callback.message,
        state=state,
        repos=repos,
        user=user,
        i18n=i18n,
        bot_timezone=bot_timezone,
        edit=True,
    )
    await callback.answer()


@bookings_router.callback_query(
    MasterAppointmentCallback.filter(F.action == "month_next"),
)
async def process_month_next(
    callback: CallbackQuery,
    state: FSMContext,
    repos: Repositories,
    user: User,
    i18n: dict[str, str],
    bot_timezone: str,
) -> None:
    await _set_month(
        state=state,
        bot_timezone=bot_timezone,
        delta_months=1,
    )
    await show_master_bookings_month(
        message=callback.message,
        state=state,
        repos=repos,
        user=user,
        i18n=i18n,
        bot_timezone=bot_timezone,
        edit=True,
    )
    await callback.answer()


@bookings_router.callback_query(
    MasterAppointmentCallback.filter(F.action == "month_current"),
)
async def process_month_current(
    callback: CallbackQuery,
    state: FSMContext,
    repos: Repositories,
    user: User,
    i18n: dict[str, str],
    bot_timezone: str,
) -> None:
    await _set_month(
        state=state,
        bot_timezone=bot_timezone,
        to_current=True,
    )
    await show_master_bookings_month(
        message=callback.message,
        state=state,
        repos=repos,
        user=user,
        i18n=i18n,
        bot_timezone=bot_timezone,
        edit=True,
    )
    await callback.answer()


@bookings_router.callback_query(MasterBookingsPadCallback.filter())
async def process_month_pad(callback: CallbackQuery) -> None:
    await callback.answer()


@bookings_router.callback_query(MasterAppointmentCallback.filter(F.action == "close"))
async def process_close(
    callback: CallbackQuery,
    state: FSMContext,
    user: User,
    i18n: dict[str, str],
    schedule_mode: str,
) -> None:
    await return_from_list(
        message=callback.message,
        user=user,
        i18n=i18n,
        state=state,
        schedule_mode=schedule_mode,
    )
    await callback.answer()
