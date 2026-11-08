"""Shared helpers for master/client appointment reschedule funnels."""

from __future__ import annotations

from datetime import datetime

from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup
from aiogram.types import Message

from app.bot.handlers.common.appointment_cancel.common import BOOKINGS_NAV_KEYS
from app.bot.handlers.common.booking_steps import (
    RESCHEDULE_APPOINTMENT_ID_KEY,
    RESCHEDULE_ORIGINAL_STARTS_AT_KEY,
    bookable_months,
    filter_reschedule_windows,
    show_months,
    unique_days,
)
from app.bot.utils.format import format_dt
from app.bot.utils.hub_nav import clear_state_keep_hub
from app.domain.models import Appointment
from app.domain.services.booking import BookingService
from app.infrastructure.database.repositories import Repositories


def reschedule_confirm_header(
    *,
    old_starts_at: datetime,
    i18n: dict[str, str],
    bot_timezone: str,
) -> str:
    return i18n.get("reschedule_old_line").format(
        when=format_dt(old_starts_at, bot_timezone),
    )


async def clear_reschedule_state(state: FSMContext) -> None:
    """Clear reschedule FSM but keep sticky hub and Bookings nav keys."""
    data = await state.get_data()
    bookings_keep = {
        key: data[key] for key in BOOKINGS_NAV_KEYS if key in data and data[key] is not None
    }
    await clear_state_keep_hub(state)
    if bookings_keep:
        await state.update_data(bookings_keep)


async def start_reschedule_funnel(
    *,
    message: Message,
    state: FSMContext,
    repos: Repositories,
    appointment: Appointment,
    states: type[StatesGroup],
    for_master: bool,
    i18n: dict[str, str],
    bot_timezone: str,
    schedule_mode: str,
    now: datetime | None = None,
) -> bool:
    """Enter month choice for a reschedule. Returns False if no windows."""
    duration_minutes = int(
        (appointment.ends_at - appointment.starts_at).total_seconds() // 60,
    )
    booking = BookingService(repos)
    exclude_id = appointment.id

    open_months = await booking.list_open_months(
        master_user_id=appointment.master_user_id,
        schedule_mode=schedule_mode,
        now=now,
    )
    if for_master:
        windows = await booking.list_windows_for_master(
            master_user_id=appointment.master_user_id,
            duration_minutes=duration_minutes,
            schedule_mode=schedule_mode,
            now=now,
            exclude_appointment_id=exclude_id,
        )
    else:
        windows = await booking.list_available_windows(
            master_user_id=appointment.master_user_id,
            duration_minutes=duration_minutes,
            schedule_mode=schedule_mode,
            now=now,
            exclude_appointment_id=exclude_id,
        )
    windows = filter_reschedule_windows(
        windows,
        {RESCHEDULE_ORIGINAL_STARTS_AT_KEY: appointment.starts_at.isoformat()},
    )
    months = bookable_months(open_months, unique_days(windows, bot_timezone))
    if not months:
        return False

    await state.update_data(
        {
            "master_user_id": appointment.master_user_id,
            "service_id": appointment.service_id,
            "service_duration": duration_minutes,
            RESCHEDULE_APPOINTMENT_ID_KEY: exclude_id,
            RESCHEDULE_ORIGINAL_STARTS_AT_KEY: appointment.starts_at.isoformat(),
            "book_year": None,
            "book_month": None,
            "day": None,
            "starts_at": None,
        }
    )
    await state.set_state(states.choosing_month)
    await show_months(message=message, months=months, i18n=i18n)
    return True
