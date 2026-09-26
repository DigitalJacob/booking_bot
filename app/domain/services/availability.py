from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from app.domain.enums import AppointmentStatus
from app.domain.models import MasterSettings, TimeWindow
from app.infrastructure.database.repositories import Repositories


def _as_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _overlaps(
        start: datetime,
        end: datetime,
        other_start: datetime,
        other_end: datetime,
) -> bool:
    return start < other_end and end > other_start


class AvailabilityService:
    def __init__(self, repos: Repositories) -> None:
        self._repos = repos

    async def list_windows(
            self,
            *,
            master_user_id: int,
            duration_minutes: int,
            now: datetime | None = None,
    ) -> list[TimeWindow]:
        if duration_minutes <= 0:
            raise ValueError("Duration_minutes must be positive")

        now = _as_utc(now or datetime.now(timezone.utc))
        settings = await self._repos.master_settings.get_by_master(
            master_user_id=master_user_id,
        )
        if settings is None:
            settings = self._default_settings(master_user_id)

        zone = ZoneInfo(settings.timezone)
        now_local = now.astimezone(zone)
        earliest = now + timedelta(minutes=settings.min_lead_minutes)

        start_day = now_local.date()
        end_day = start_day + timedelta(days=settings.booking_horizon_days)

        range_from = datetime.combine(start_day, time.min, tzinfo=zone)
        range_to = datetime.combine(end_day, time.min, tzinfo=zone)

        working = await self._repos.working_hours.list_by_master(
            master_user_id=master_user_id,
        )
        by_weekday: dict[int, list] = {}
        for row in working:
            by_weekday.setdefault(row.weekday, []).append(row)

        time_offs = await self._repos.time_off.list_by_master(
            master_user_id=master_user_id,
            from_dt=range_from,
            to_dt=range_to,
        )
        appointments = await self._repos.appointments.list_by_master(
            master_user_id=master_user_id,
            from_dt=range_from,
            to_dt=range_to,
        )
        busy: list[tuple[datetime, datetime]] = []
        for block in time_offs:
            busy.append((_as_utc(block.starts_at), _as_utc(block.ends_at)))
        gap = timedelta(minutes=settings.gap_minutes)
        for appointment in appointments:
            if appointment.status not in (
                AppointmentStatus.PENDING,
                AppointmentStatus.CONFIRMED,
            ):
                continue
            busy.append((
                _as_utc(appointment.starts_at),
                _as_utc(appointment.ends_at) + gap,
            ))

        step_minutes = settings.slot_step_minutes or duration_minutes
        step = timedelta(minutes=step_minutes)
        duration = timedelta(minutes=duration_minutes)

        windows: list[TimeWindow] = []
        day = start_day
        while day < end_day:
            for wh in by_weekday.get(day.isoweekday(), []):
                day_start = datetime.combine(
                    day, wh.starts_time, tzinfo=zone,
                )
                day_end = datetime.combine(
                    day, wh.ends_time, tzinfo=zone,
                )
                cursor = day_start
                while cursor + duration <= day_end:
                    end = cursor + duration
                    start_utc = _as_utc(cursor)
                    end_utc = _as_utc(end)

                    if start_utc < earliest:
                        cursor += step
                        continue

                    blocking_ends = [
                        b1
                        for b0, b1 in busy
                        if _overlaps(start_utc, end_utc, b0, b1)
                    ]
                    if blocking_ends:
                        # Jump to the end of the blocking busy (includes gap).
                        jump_to = max(blocking_ends).astimezone(zone)
                        if jump_to <= cursor:
                            cursor += step
                        else:
                            cursor = jump_to
                        continue

                    windows.append(
                        TimeWindow(starts_at=start_utc, ends_at=end_utc),
                    )
                    cursor += step
            day += timedelta(days=1)

        return windows

    @staticmethod
    def _default_settings(master_user_id: int) -> MasterSettings:
        now = datetime.now(timezone.utc)
        return MasterSettings(
            master_user_id=master_user_id,
            timezone="Europe/Moscow",
            slot_step_minutes=None,
            gap_minutes=0,
            min_lead_minutes=0,
            booking_horizon_days=30,
            created_at=now,
            updated_at=now,
        )
