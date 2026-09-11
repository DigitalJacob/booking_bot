from datetime import date, datetime, time, timezone, timedelta
from zoneinfo import ZoneInfo

from app.domain.enums import AppointmentStatus
from app.domain.models import User


_STATUS_KEYS = {
    AppointmentStatus.PENDING: "status_pending",
    AppointmentStatus.CONFIRMED: "status_confirmed",
    AppointmentStatus.CANCELLED: "status_cancelled",
}


def status_label(status: AppointmentStatus, i18n: dict[str, str]) -> str:
    return i18n.get(_STATUS_KEYS[status])


def client_contact(user: User | None) -> tuple[str, str]:
    if user is None:
        return "?", "-"
    phone = user.phone or "-"
    return user.display_name, phone


def get_zone(tz_name: str) -> ZoneInfo:
    return ZoneInfo(tz_name)


def to_local(dt: datetime, tz_name: str) -> datetime:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(get_zone(tz_name))


def combine_local(
        day: date,
        time_part: time,
        tz_name: str,
) -> datetime:
    """Interpret wall-clock date+time in bot timezone, return aware UTC-comparable datetime."""
    local = datetime.combine(day, time_part, tzinfo=get_zone(tz_name))
    return local


def format_dt(
        dt: datetime | None,
        tz_name: str,
        fmt: str = "%d.%m.%Y %H:%M",
        fallback: str = "?",
) -> str:
    if dt is None:
        return fallback
    return to_local(dt, tz_name).strftime(fmt)


def format_time(
        dt: datetime | None,
        tz_name: str,
        fallback: str = "?",
) -> str:
    return format_dt(dt, tz_name, fmt="%H:%M", fallback=fallback)


def local_today_bounds(tz_name: str) -> tuple[datetime, datetime]:
    """Start of today and start of tomorrow in bot TZ, as aware datetimes."""
    zone = get_zone(tz_name)
    now_local = datetime.now(zone)
    start_local = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
    end_local = start_local + timedelta(days=1)
    return start_local, end_local
