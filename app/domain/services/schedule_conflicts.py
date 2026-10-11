"""Find active appointments that conflict with schedule edits."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from app.domain.enums import AppointmentStatus
from app.domain.models import Appointment
from app.domain.ports import RepositoriesPort
from app.domain.time_range import as_utc, intervals_overlap

_ACTIVE = frozenset({AppointmentStatus.PENDING, AppointmentStatus.CONFIRMED})


class ScheduleConflictsService:
    def __init__(self, repos: RepositoriesPort) -> None:
        self._repos = repos

    async def active_overlapping(
        self,
        *,
        master_user_id: int,
        starts_at: datetime,
        ends_at: datetime,
    ) -> list[Appointment]:
        """Active appointments overlapping ``[starts_at, ends_at)``.

        ``list_by_master`` filters on ``starts_at``, so the query window is
        widened one day left to catch slots that began before the block but
        still overlap; precise filtering uses ``intervals_overlap``.
        """
        block_start = as_utc(starts_at)
        block_end = as_utc(ends_at)
        rows = await self._repos.appointments.list_by_master(
            master_user_id=master_user_id,
            from_dt=block_start - timedelta(days=1),
            to_dt=block_end,
        )
        result: list[Appointment] = []
        for appointment in rows:
            if appointment.status not in _ACTIVE:
                continue
            if intervals_overlap(
                block_start,
                block_end,
                as_utc(appointment.starts_at),
                as_utc(appointment.ends_at),
            ):
                result.append(appointment)
        return result

    async def active_on_local_days(
        self,
        *,
        master_user_id: int,
        days: set[date],
        timezone: str,
    ) -> list[Appointment]:
        """Active appointments whose local start date is in ``days``."""
        if not days:
            return []

        zone = ZoneInfo(timezone)
        from_day = min(days)
        to_day = max(days) + timedelta(days=1)
        rows = await self._repos.appointments.list_by_master(
            master_user_id=master_user_id,
            from_dt=datetime.combine(from_day, time.min, tzinfo=zone),
            to_dt=datetime.combine(to_day, time.min, tzinfo=zone),
        )
        result: list[Appointment] = []
        for appointment in rows:
            if appointment.status not in _ACTIVE:
                continue
            local_day = as_utc(appointment.starts_at).astimezone(zone).date()
            if local_day in days:
                result.append(appointment)
        return result
