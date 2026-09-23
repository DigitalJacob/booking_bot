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


def local_week_bounds(
        tz_name: str,
        *,
        week_start: date | None = None,
) -> tuple[datetime, datetime, date]:
    """
    Monday 00:00 .. next Monday 00:00 in bot TZ.
    If week_start is None, use the Monday of the current local week.
    """
    zone = get_zone(tz_name)
    if week_start is None:
        today = datetime.now(zone).date()
        week_start = today - timedelta(days=today.isoweekday() - 1)
    start_local = datetime.combine(week_start, time.min, tzinfo=zone)
    end_local = start_local + timedelta(days=7)
    return start_local, end_local, week_start


def _plural_form_index(n: int) -> int:
    """0=one, 1=few, 2=many (Slavic rules; EN can use few==many)."""
    n = abs(n) % 100
    if 10 < n < 20:
        return 2
    last = n % 10
    if last == 1:
        return 0
    if last in (2, 3, 4):
        return 1
    return 2


def i18n_plural(
        n: int,
        i18n: dict[str, str],
        *,
        key_prefix: str,
        **extra: object,
) -> str:
    suffix = ("one", "few", "many")[_plural_form_index(n)]
    return i18n.get(f"{key_prefix}_{suffix}").format(n=n, **extra)
