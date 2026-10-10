from datetime import date, datetime, time, timedelta, timezone
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
            schedule_mode: str = "weekly",
            now: datetime | None = None,
    ) -> list[TimeWindow]:
        if duration_minutes <= 0:
            raise ValueError("Duration_minutes must be positive")
        if schedule_mode not in ("weekly", "monthly"):
            raise ValueError(
                f"schedule_mode must be 'weekly' or 'monthly', "
                f"got: {schedule_mode!r}"
            )

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

        by_weekday: dict[int, list] = {}
        by_date: dict[date, list] = {}
        if schedule_mode == "monthly":
            work_dates = await self._repos.work_dates.list_by_master(
                master_user_id=master_user_id,
                from_date=start_day,
                to_date=end_day,
            )
            for work_date in work_dates:
                by_date.setdefault(work_date.work_date, []).append(work_date)
        else:
            working = await self._repos.working_hours.list_by_master(
                master_user_id=master_user_id,
            )
            for hours in working:
                by_weekday.setdefault(hours.weekday, []).append(hours)

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
            if schedule_mode == "monthly":
                intervals = by_date.get(day, [])
            else:
                intervals = by_weekday.get(day.isoweekday(), [])

            for interval in intervals:
                day_start = datetime.combine(
                    day, interval.starts_time, tzinfo=zone,
                )
                day_end = datetime.combine(
                    day, interval.ends_time, tzinfo=zone,
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

    async def list_open_months(
            self,
            *,
            master_user_id: int,
            schedule_mode: str = "weekly",
            now: datetime | None = None,
    ) -> list[tuple[int, int]]:
        """Months inside the booking horizon that have at least one open day.

        monthly: months with a ``work_dates`` row on/after today (within horizon).
        weekly: months that contain a horizon day matching ``working_hours``.
        """
        if schedule_mode not in ("weekly", "monthly"):
            raise ValueError(
                f"schedule_mode must be 'weekly' or 'monthly', "
                f"got: {schedule_mode!r}"
            )

        now = _as_utc(now or datetime.now(timezone.utc))
        settings = await self._repos.master_settings.get_by_master(
            master_user_id=master_user_id,
        )
        if settings is None:
            settings = self._default_settings(master_user_id)

        zone = ZoneInfo(settings.timezone)
        start_day = now.astimezone(zone).date()
        end_day = start_day + timedelta(days=settings.booking_horizon_days)

        months: set[tuple[int, int]] = set()
        if schedule_mode == "monthly":
            work_dates = await self._repos.work_dates.list_by_master(
                master_user_id=master_user_id,
                from_date=start_day,
                to_date=end_day,
            )
            for row in work_dates:
                months.add((row.work_date.year, row.work_date.month))
        else:
            working = await self._repos.working_hours.list_by_master(
                master_user_id=master_user_id,
            )
            open_weekdays = {row.weekday for row in working}
            if open_weekdays:
                day = start_day
                while day < end_day:
                    if day.isoweekday() in open_weekdays:
                        months.add((day.year, day.month))
                    day += timedelta(days=1)

        return sorted(months)

    @staticmethod
    def _default_settings(master_user_id: int) -> MasterSettings:
        now = datetime.now(timezone.utc)
        return MasterSettings(
            master_user_id=master_user_id,
            timezone="Europe/Moscow",
            slot_step_minutes=None,
            gap_minutes=0,
            min_lead_minutes=0,
            booking_horizon_days=180,
            created_at=now,
            updated_at=now,
        )
