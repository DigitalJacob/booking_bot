"""Shared helpers and FSM keys for master bookings views."""

from __future__ import annotations

from datetime import date, timedelta

from aiogram.fsm.context import FSMContext

from app.bot.keyboards.schedule import WEEKDAY_KEYS
from app.bot.utils.format import local_month_bounds, local_week_bounds, to_local
from app.domain.enums import AppointmentStatus
from app.domain.models import Appointment, User
from app.infrastructure.database.repositories import Repositories

BUTTON_LABEL_MAX = 64
WEEK_START_KEY = "bookings_week_start"
MONTH_KEY = "bookings_month"  # YYYY-MM
DAY_KEY = "bookings_day"


def parse_iso_date(raw: str | None) -> date | None:
    if not raw:
        return None
    try:
        return date.fromisoformat(raw)
    except ValueError:
        return None


def bookings_back_to(schedule_mode: str) -> str:
    return "month" if schedule_mode == "monthly" else "week"


async def back_to_from_state(state: FSMContext) -> str:
    data = await state.get_data()
    return "month" if data.get(MONTH_KEY) else "week"


def week_range_label(week_start: date) -> str:
    last = week_start + timedelta(days=6)
    return f"{week_start.strftime('%d.%m')}–{last.strftime('%d.%m')}"


def day_label(*, day: date, i18n: dict[str, str]) -> str:
    weekday = i18n.get(WEEKDAY_KEYS[day.isoweekday()])
    return f"{weekday} {day.strftime('%d.%m')}"


def truncate_button(text: str) -> str:
    if len(text) > BUTTON_LABEL_MAX:
        return text[: BUTTON_LABEL_MAX - 1] + "…"
    return text


def active_only(appointments: list[Appointment]) -> list[Appointment]:
    return [
        a
        for a in appointments
        if a.status in (AppointmentStatus.PENDING, AppointmentStatus.CONFIRMED)
    ]


def counts_by_local_day(
    *,
    appointments: list[Appointment],
    bot_timezone: str,
) -> dict[date, int]:
    counts: dict[date, int] = {}
    for appointment in appointments:
        day = to_local(appointment.starts_at, bot_timezone).date()
        counts[day] = counts.get(day, 0) + 1
    return counts


async def load_week_active(
    *,
    repos: Repositories,
    user: User,
    bot_timezone: str,
    week_start: date | None,
) -> tuple[date, list[Appointment], bool]:
    from_dt, to_dt, week_start = local_week_bounds(
        bot_timezone,
        week_start=week_start,
    )
    appointments = await repos.appointments.list_by_master(
        master_user_id=user.user_id,
        from_dt=from_dt,
        to_dt=to_dt,
    )
    active = active_only(appointments)
    _, _, current_week_start = local_week_bounds(bot_timezone)
    return week_start, active, week_start == current_week_start


async def load_month_active(
    *,
    repos: Repositories,
    user: User,
    bot_timezone: str,
    year: int | None,
    month: int | None,
) -> tuple[int, int, list[Appointment], bool]:
    from_dt, to_dt, year, month = local_month_bounds(
        bot_timezone,
        year=year,
        month=month,
    )
    appointments = await repos.appointments.list_by_master(
        master_user_id=user.user_id,
        from_dt=from_dt,
        to_dt=to_dt,
    )
    active = active_only(appointments)
    _, _, current_year, current_month = local_month_bounds(bot_timezone)
    is_current = (year, month) == (current_year, current_month)
    return year, month, active, is_current
