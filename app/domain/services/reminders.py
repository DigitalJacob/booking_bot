"""Pure rules for when a confirmed appointment is due for a reminder push."""

from datetime import UTC, datetime, timedelta
from typing import cast
from zoneinfo import ZoneInfo

from app.domain.enums.appointment import AppointmentStatus
from app.domain.enums.reminder import ReminderKind, reminded_at_attr
from app.domain.models.appointment import Appointment


def reminded_at_for(
        appointment: Appointment,
        kind: ReminderKind,
) -> datetime | None:
    return cast(
        datetime | None,
        getattr(appointment, reminded_at_attr(kind)),
    )


def _as_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def is_hour_reminder_due(
        *,
        appointment: Appointment,
        kind: ReminderKind,
        now: datetime,
        lead_minutes: int,
) -> bool:
    if kind not in (ReminderKind.CLIENT_HOUR, ReminderKind.MASTER_HOUR):
        return False
    if appointment.status != AppointmentStatus.CONFIRMED:
        return False
    if reminded_at_for(appointment, kind) is not None:
        return False
    if lead_minutes <= 0:
        return False

    now_utc = _as_utc(now)
    starts = _as_utc(appointment.starts_at)
    if now_utc >= starts:
        return False
    return now_utc >= starts - timedelta(minutes=lead_minutes)


def is_evening_reminder_due(
        *,
        appointment: Appointment,
        kind: ReminderKind,
        now: datetime,
        timezone_name: str,
        evening_hour_start: int,
        evening_hour_end: int,
) -> bool:
    """
    Evening window is half-open [evening_hour_start, evening_hour_end)
    on the local calendar day before the appointment's local day.
    """
    if kind not in (ReminderKind.CLIENT_EVENING, ReminderKind.MASTER_EVENING):
        return False
    if appointment.status != AppointmentStatus.CONFIRMED:
        return False
    if reminded_at_for(appointment, kind) is not None:
        return False
    if not (0 <= evening_hour_start < evening_hour_end <= 24):
        return False

    tz = ZoneInfo(timezone_name)
    local_now = _as_utc(now).astimezone(tz)
    if not (evening_hour_start <= local_now.hour < evening_hour_end):
        return False

    starts_local = _as_utc(appointment.starts_at).astimezone(tz)
    return starts_local.date() == (local_now.date() + timedelta(days=1))


def is_reminder_due(
        *,
        appointment: Appointment,
        kind: ReminderKind,
        now: datetime,
        timezone_name: str,
        lead_minutes: int,
        evening_hour_start: int,
        evening_hour_end: int,
) -> bool:
    if kind in (ReminderKind.CLIENT_HOUR, ReminderKind.MASTER_HOUR):
        return is_hour_reminder_due(
            appointment=appointment,
            kind=kind,
            now=now,
            lead_minutes=lead_minutes,
        )
    return is_evening_reminder_due(
        appointment=appointment,
        kind=kind,
        now=now,
        timezone_name=timezone_name,
        evening_hour_start=evening_hour_start,
        evening_hour_end=evening_hour_end,
    )


def filter_due_reminders(
        *,
        appointments: list[Appointment],
        kind: ReminderKind,
        now: datetime,
        timezone_name: str,
        lead_minutes: int,
        evening_hour_start: int,
        evening_hour_end: int,
) -> list[Appointment]:
    return [
        appointment
        for appointment in appointments
        if is_reminder_due(
            appointment=appointment,
            kind=kind,
            now=now,
            timezone_name=timezone_name,
            lead_minutes=lead_minutes,
            evening_hour_start=evening_hour_start,
            evening_hour_end=evening_hour_end,
        )
    ]
