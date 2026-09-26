from datetime import datetime, time, timezone
from typing import cast

import pytest

from app.domain.enums import AppointmentStatus
from app.domain.models import (
    Appointment,
    MasterSettings,
    TimeOff,
    WorkingHours,
)
from app.domain.services.availability import AvailabilityService
from app.infrastructure.database.repositories import (
    AppointmentsRepository,
    MasterSettingsRepository,
    Repositories,
    ServicesRepository,
    TimeOffRepository,
    UsersRepository,
    WorkingHoursRepository,
)


MASTER_ID = 100
# Thursday 2026-09-10 — isoweekday() == 4
NOW = datetime(2026, 9, 10, 5, 0, tzinfo=timezone.utc)
CREATED = NOW


def _settings(
        *,
        slot_step_minutes: int | None = None,
        gap_minutes: int = 0,
        min_lead_minutes: int = 0,
        booking_horizon_days: int = 7,
) -> MasterSettings:
    return MasterSettings(
        master_user_id=MASTER_ID,
        timezone="Europe/Moscow",
        slot_step_minutes=slot_step_minutes,
        gap_minutes=gap_minutes,
        min_lead_minutes=min_lead_minutes,
        booking_horizon_days=booking_horizon_days,
        created_at=CREATED,
        updated_at=CREATED,
    )


def _working(
        *,
        weekday: int = 4,
        starts: time = time(9, 0),
        ends: time = time(12, 0),
        row_id: int = 1,
) -> WorkingHours:
    return WorkingHours(
        id=row_id,
        master_user_id=MASTER_ID,
        weekday=weekday,
        starts_time=starts,
        ends_time=ends,
        created_at=CREATED,
    )


def _appointment(
        *,
        starts_at: datetime,
        ends_at: datetime,
        status: AppointmentStatus = AppointmentStatus.PENDING,
        appointment_id: int = 1,
) -> Appointment:
    return Appointment(
        id=appointment_id,
        client_user_id=200,
        master_user_id=MASTER_ID,
        service_id=1,
        starts_at=starts_at,
        ends_at=ends_at,
        status=status,
        created_at=CREATED,
    )


def _time_off(
        *,
        starts_at: datetime,
        ends_at: datetime,
        row_id: int = 1,
) -> TimeOff:
    return TimeOff(
        id=row_id,
        master_user_id=MASTER_ID,
        starts_at=starts_at,
        ends_at=ends_at,
        note=None,
        created_at=CREATED,
    )


class FakeMasterSettingsRepository:
    def __init__(self, settings: MasterSettings | None) -> None:
        self._settings = settings

    async def get_by_master(self, *, master_user_id: int) -> MasterSettings | None:
        if self._settings and self._settings.master_user_id == master_user_id:
            return self._settings
        return None


class FakeWorkingHoursRepository:
    def __init__(self, rows: list[WorkingHours]) -> None:
        self._rows = rows

    async def list_by_master(
            self,
            *,
            master_user_id: int,
            weekday: int | None = None,
    ) -> list[WorkingHours]:
        result = [
            row for row in self._rows
            if row.master_user_id == master_user_id
            and (weekday is None or row.weekday == weekday)
        ]
        return sorted(result, key=lambda row: (row.weekday, row.starts_time))


class FakeTimeOffRepository:
    def __init__(self, rows: list[TimeOff]) -> None:
        self._rows = rows

    async def list_by_master(
            self,
            *,
            master_user_id: int,
            from_dt: datetime | None = None,
            to_dt: datetime | None = None,
    ) -> list[TimeOff]:
        result = []
        for row in self._rows:
            if row.master_user_id != master_user_id:
                continue
            if from_dt is not None and row.ends_at <= from_dt:
                continue
            if to_dt is not None and row.starts_at >= to_dt:
                continue
            result.append(row)
        return sorted(result, key=lambda row: row.starts_at)


class FakeAppointmentsRepository:
    def __init__(self, rows: list[Appointment]) -> None:
        self._rows = rows

    async def list_by_master(
            self,
            *,
            master_user_id: int,
            from_dt: datetime | None = None,
            to_dt: datetime | None = None,
    ) -> list[Appointment]:
        result = []
        for row in self._rows:
            if row.master_user_id != master_user_id:
                continue
            if from_dt is not None and row.starts_at < from_dt:
                continue
            if to_dt is not None and row.starts_at >= to_dt:
                continue
            result.append(row)
        return sorted(result, key=lambda row: row.starts_at)


def make_availability_repos(
        *,
        settings: MasterSettings | None = None,
        working_hours: list[WorkingHours] | None = None,
        time_offs: list[TimeOff] | None = None,
        appointments: list[Appointment] | None = None,
) -> Repositories:
    return Repositories(
        users=cast(UsersRepository, None),
        services=cast(ServicesRepository, None),
        appointments=cast(
            AppointmentsRepository,
            FakeAppointmentsRepository(appointments or []),
        ),
        master_settings=cast(
            MasterSettingsRepository,
            FakeMasterSettingsRepository(settings),
        ),
        working_hours=cast(
            WorkingHoursRepository,
            FakeWorkingHoursRepository(working_hours or []),
        ),
        time_off=cast(
            TimeOffRepository,
            FakeTimeOffRepository(time_offs or []),
        ),
    )


def _starts(windows) -> list[datetime]:
    return [window.starts_at for window in windows]


@pytest.mark.asyncio
async def test_basic_grid_on_working_hours():
    """Thu 09:00-12:00 MSK, 60-min service, step=duration → 09, 10, 11."""
    repos = make_availability_repos(
        settings=_settings(booking_horizon_days=1),
        working_hours=[_working()],
    )
    service = AvailabilityService(repos)

    windows = await service.list_windows(
        master_user_id=MASTER_ID,
        duration_minutes=60,
        now=NOW,
    )

    # 09:00 MSK = 06:00 UTC, etc.
    assert _starts(windows) == [
        datetime(2026, 9, 10, 6, 0, tzinfo=timezone.utc),
        datetime(2026, 9, 10, 7, 0, tzinfo=timezone.utc),
        datetime(2026, 9, 10, 8, 0, tzinfo=timezone.utc),
    ]


@pytest.mark.asyncio
async def test_appointment_blocks_window():
    """Existing 10:00-11:00 MSK booking removes that candidate."""
    busy_start = datetime(2026, 9, 10, 7, 0, tzinfo=timezone.utc)  # 10:00 MSK
    busy_end = datetime(2026, 9, 10, 8, 0, tzinfo=timezone.utc)    # 11:00 MSK
    repos = make_availability_repos(
        settings=_settings(booking_horizon_days=1),
        working_hours=[_working()],
        appointments=[_appointment(starts_at=busy_start, ends_at=busy_end)],
    )
    service = AvailabilityService(repos)

    windows = await service.list_windows(
        master_user_id=MASTER_ID,
        duration_minutes=60,
        now=NOW,
    )

    assert _starts(windows) == [
        datetime(2026, 9, 10, 6, 0, tzinfo=timezone.utc),
        datetime(2026, 9, 10, 8, 0, tzinfo=timezone.utc),
    ]


@pytest.mark.asyncio
async def test_time_off_blocks_window():
    block_start = datetime(2026, 9, 10, 7, 0, tzinfo=timezone.utc)
    block_end = datetime(2026, 9, 10, 8, 0, tzinfo=timezone.utc)
    repos = make_availability_repos(
        settings=_settings(booking_horizon_days=1),
        working_hours=[_working()],
        time_offs=[_time_off(starts_at=block_start, ends_at=block_end)],
    )
    service = AvailabilityService(repos)

    windows = await service.list_windows(
        master_user_id=MASTER_ID,
        duration_minutes=60,
        now=NOW,
    )

    assert _starts(windows) == [
        datetime(2026, 9, 10, 6, 0, tzinfo=timezone.utc),
        datetime(2026, 9, 10, 8, 0, tzinfo=timezone.utc),
    ]


@pytest.mark.asyncio
async def test_gap_after_appointment():
    """gap=15: booking ending 10:00 MSK → next start not before 10:15."""
    busy_start = datetime(2026, 9, 10, 6, 0, tzinfo=timezone.utc)  # 09:00
    busy_end = datetime(2026, 9, 10, 7, 0, tzinfo=timezone.utc)    # 10:00
    repos = make_availability_repos(
        settings=_settings(
            slot_step_minutes=15,
            gap_minutes=15,
            booking_horizon_days=1,
        ),
        working_hours=[_working()],
        appointments=[_appointment(starts_at=busy_start, ends_at=busy_end)],
    )
    service = AvailabilityService(repos)

    windows = await service.list_windows(
        master_user_id=MASTER_ID,
        duration_minutes=60,
        now=NOW,
    )

    starts = _starts(windows)
    assert datetime(2026, 9, 10, 6, 0, tzinfo=timezone.utc) not in starts
    assert datetime(2026, 9, 10, 7, 0, tzinfo=timezone.utc) not in starts
    assert datetime(2026, 9, 10, 7, 15, tzinfo=timezone.utc) in starts


@pytest.mark.asyncio
async def test_gap_advances_cursor_when_step_is_coarser():
    """Default step (= duration 60) + gap 15 → next start at 10:15, not 11:00."""
    busy_start = datetime(2026, 9, 10, 6, 0, tzinfo=timezone.utc)  # 09:00
    busy_end = datetime(2026, 9, 10, 7, 0, tzinfo=timezone.utc)    # 10:00
    repos = make_availability_repos(
        settings=_settings(
            slot_step_minutes=None,
            gap_minutes=15,
            booking_horizon_days=1,
        ),
        working_hours=[_working()],
        appointments=[_appointment(starts_at=busy_start, ends_at=busy_end)],
    )
    service = AvailabilityService(repos)

    windows = await service.list_windows(
        master_user_id=MASTER_ID,
        duration_minutes=60,
        now=NOW,
    )

    starts = _starts(windows)
    assert datetime(2026, 9, 10, 6, 0, tzinfo=timezone.utc) not in starts
    assert datetime(2026, 9, 10, 7, 0, tzinfo=timezone.utc) not in starts
    assert datetime(2026, 9, 10, 7, 15, tzinfo=timezone.utc) in starts
    assert datetime(2026, 9, 10, 8, 0, tzinfo=timezone.utc) not in starts


@pytest.mark.asyncio
async def test_min_lead_filters_early_slots():
    """now=10:30 MSK, min_lead=0 → 09:00 and 10:00 already gone."""
    now = datetime(2026, 9, 10, 7, 30, tzinfo=timezone.utc)  # 10:30 MSK
    repos = make_availability_repos(
        settings=_settings(booking_horizon_days=1),
        working_hours=[_working()],
    )
    service = AvailabilityService(repos)

    windows = await service.list_windows(
        master_user_id=MASTER_ID,
        duration_minutes=60,
        now=now,
    )

    assert _starts(windows) == [
        datetime(2026, 9, 10, 8, 0, tzinfo=timezone.utc),  # 11:00 MSK
    ]


@pytest.mark.asyncio
async def test_cancelled_appointment_does_not_block():
    busy_start = datetime(2026, 9, 10, 7, 0, tzinfo=timezone.utc)
    busy_end = datetime(2026, 9, 10, 8, 0, tzinfo=timezone.utc)
    repos = make_availability_repos(
        settings=_settings(booking_horizon_days=1),
        working_hours=[_working()],
        appointments=[
            _appointment(
                starts_at=busy_start,
                ends_at=busy_end,
                status=AppointmentStatus.CANCELLED,
            ),
        ],
    )
    service = AvailabilityService(repos)

    windows = await service.list_windows(
        master_user_id=MASTER_ID,
        duration_minutes=60,
        now=NOW,
    )

    assert len(windows) == 3
