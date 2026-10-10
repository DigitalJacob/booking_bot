from datetime import UTC, date, datetime, time

import pytest
from app.domain.enums import AppointmentStatus
from app.domain.models import (
    Appointment,
    MasterSettings,
    TimeOff,
    WorkDate,
    WorkingHours,
)
from app.domain.ports import RepositoriesPort
from app.domain.services.availability import AvailabilityService

from tests.factories import make_repos

MASTER_ID = 100
# Thursday 2026-09-10 — isoweekday() == 4
NOW = datetime(2026, 9, 10, 5, 0, tzinfo=UTC)
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


def _work_date(
        *,
        work_date: date,
        starts: time = time(9, 0),
        ends: time = time(12, 0),
        row_id: int = 1,
) -> WorkDate:
    return WorkDate(
        id=row_id,
        master_user_id=MASTER_ID,
        work_date=work_date,
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


def make_availability_repos(
        *,
        settings: MasterSettings | None = None,
        working_hours: list[WorkingHours] | None = None,
        work_dates: list[WorkDate] | None = None,
        time_offs: list[TimeOff] | None = None,
        appointments: list[Appointment] | None = None,
) -> RepositoriesPort:
    return make_repos(
        settings=settings,
        working_hours=working_hours,
        work_dates=work_dates,
        time_offs=time_offs,
        appointments=appointments,
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
        datetime(2026, 9, 10, 6, 0, tzinfo=UTC),
        datetime(2026, 9, 10, 7, 0, tzinfo=UTC),
        datetime(2026, 9, 10, 8, 0, tzinfo=UTC),
    ]


@pytest.mark.asyncio
async def test_appointment_blocks_window():
    """Existing 10:00-11:00 MSK booking removes that candidate."""
    busy_start = datetime(2026, 9, 10, 7, 0, tzinfo=UTC)  # 10:00 MSK
    busy_end = datetime(2026, 9, 10, 8, 0, tzinfo=UTC)    # 11:00 MSK
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
        datetime(2026, 9, 10, 6, 0, tzinfo=UTC),
        datetime(2026, 9, 10, 8, 0, tzinfo=UTC),
    ]


@pytest.mark.asyncio
async def test_time_off_blocks_window():
    block_start = datetime(2026, 9, 10, 7, 0, tzinfo=UTC)
    block_end = datetime(2026, 9, 10, 8, 0, tzinfo=UTC)
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
        datetime(2026, 9, 10, 6, 0, tzinfo=UTC),
        datetime(2026, 9, 10, 8, 0, tzinfo=UTC),
    ]


@pytest.mark.asyncio
async def test_gap_after_appointment():
    """gap=15: booking ending 10:00 MSK → next start not before 10:15."""
    busy_start = datetime(2026, 9, 10, 6, 0, tzinfo=UTC)  # 09:00
    busy_end = datetime(2026, 9, 10, 7, 0, tzinfo=UTC)    # 10:00
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
    assert datetime(2026, 9, 10, 6, 0, tzinfo=UTC) not in starts
    assert datetime(2026, 9, 10, 7, 0, tzinfo=UTC) not in starts
    assert datetime(2026, 9, 10, 7, 15, tzinfo=UTC) in starts


@pytest.mark.asyncio
async def test_gap_advances_cursor_when_step_is_coarser():
    """Default step (= duration 60) + gap 15 → next start at 10:15, not 11:00."""
    busy_start = datetime(2026, 9, 10, 6, 0, tzinfo=UTC)  # 09:00
    busy_end = datetime(2026, 9, 10, 7, 0, tzinfo=UTC)    # 10:00
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
    assert datetime(2026, 9, 10, 6, 0, tzinfo=UTC) not in starts
    assert datetime(2026, 9, 10, 7, 0, tzinfo=UTC) not in starts
    assert datetime(2026, 9, 10, 7, 15, tzinfo=UTC) in starts
    assert datetime(2026, 9, 10, 8, 0, tzinfo=UTC) not in starts


@pytest.mark.asyncio
async def test_min_lead_filters_early_slots():
    """now=10:30 MSK, min_lead=0 → 09:00 and 10:00 already gone."""
    now = datetime(2026, 9, 10, 7, 30, tzinfo=UTC)  # 10:30 MSK
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
        datetime(2026, 9, 10, 8, 0, tzinfo=UTC),  # 11:00 MSK
    ]


@pytest.mark.asyncio
async def test_cancelled_appointment_does_not_block():
    busy_start = datetime(2026, 9, 10, 7, 0, tzinfo=UTC)
    busy_end = datetime(2026, 9, 10, 8, 0, tzinfo=UTC)
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


@pytest.mark.asyncio
async def test_monthly_open_day_builds_grid():
    """Open 2026-09-10 in work_dates → same 09/10/11 MSK grid as weekly."""
    repos = make_availability_repos(
        settings=_settings(booking_horizon_days=1),
        work_dates=[_work_date(work_date=date(2026, 9, 10))],
    )
    service = AvailabilityService(repos)

    windows = await service.list_windows(
        master_user_id=MASTER_ID,
        duration_minutes=60,
        schedule_mode="monthly",
        now=NOW,
    )

    assert _starts(windows) == [
        datetime(2026, 9, 10, 6, 0, tzinfo=UTC),
        datetime(2026, 9, 10, 7, 0, tzinfo=UTC),
        datetime(2026, 9, 10, 8, 0, tzinfo=UTC),
    ]


@pytest.mark.asyncio
async def test_monthly_empty_day_has_no_windows():
    """Horizon day without work_dates row → no slots (weekly hours ignored)."""
    repos = make_availability_repos(
        settings=_settings(booking_horizon_days=1),
        working_hours=[_working()],
        work_dates=[],
    )
    service = AvailabilityService(repos)

    windows = await service.list_windows(
        master_user_id=MASTER_ID,
        duration_minutes=60,
        schedule_mode="monthly",
        now=NOW,
    )

    assert windows == []


@pytest.mark.asyncio
async def test_monthly_time_off_blocks_window():
    repos = make_availability_repos(
        settings=_settings(booking_horizon_days=1),
        work_dates=[_work_date(work_date=date(2026, 9, 10))],
        time_offs=[
            _time_off(
                starts_at=datetime(2026, 9, 10, 7, 0, tzinfo=UTC),
                ends_at=datetime(2026, 9, 10, 8, 0, tzinfo=UTC),
            ),
        ],
    )
    service = AvailabilityService(repos)

    windows = await service.list_windows(
        master_user_id=MASTER_ID,
        duration_minutes=60,
        schedule_mode="monthly",
        now=NOW,
    )

    assert _starts(windows) == [
        datetime(2026, 9, 10, 6, 0, tzinfo=UTC),
        datetime(2026, 9, 10, 8, 0, tzinfo=UTC),
    ]


@pytest.mark.asyncio
async def test_weekly_ignores_work_dates():
    """weekly mode still uses weekday hours, not work_dates."""
    repos = make_availability_repos(
        settings=_settings(booking_horizon_days=1),
        working_hours=[_working()],
        work_dates=[],
    )
    service = AvailabilityService(repos)

    windows = await service.list_windows(
        master_user_id=MASTER_ID,
        duration_minutes=60,
        schedule_mode="weekly",
        now=NOW,
    )

    assert len(windows) == 3


@pytest.mark.asyncio
async def test_list_open_months_monthly_from_work_dates():
    """Months with work_dates inside the horizon; past-only / out-of-horizon skipped."""
    repos = make_availability_repos(
        settings=_settings(booking_horizon_days=40),
        work_dates=[
            _work_date(work_date=date(2026, 9, 1), row_id=1),  # before today
            _work_date(work_date=date(2026, 9, 10), row_id=2),
            _work_date(work_date=date(2026, 10, 5), row_id=3),
            _work_date(work_date=date(2026, 11, 1), row_id=4),  # past horizon
        ],
    )
    service = AvailabilityService(repos)

    months = await service.list_open_months(
        master_user_id=MASTER_ID,
        schedule_mode="monthly",
        now=NOW,
    )

    assert months == [(2026, 9), (2026, 10)]


@pytest.mark.asyncio
async def test_list_open_months_monthly_empty():
    repos = make_availability_repos(
        settings=_settings(booking_horizon_days=30),
        work_dates=[],
    )
    service = AvailabilityService(repos)

    months = await service.list_open_months(
        master_user_id=MASTER_ID,
        schedule_mode="monthly",
        now=NOW,
    )

    assert months == []


@pytest.mark.asyncio
async def test_list_open_months_weekly_from_working_hours():
    """weekly: months that contain a horizon day matching open weekdays."""
    # Thursday-only hours; horizon covers Sep 10..17 → Sep only.
    repos = make_availability_repos(
        settings=_settings(booking_horizon_days=7),
        working_hours=[_working(weekday=4)],
    )
    service = AvailabilityService(repos)

    months = await service.list_open_months(
        master_user_id=MASTER_ID,
        schedule_mode="weekly",
        now=NOW,
    )

    assert months == [(2026, 9)]
