from datetime import datetime, time, timezone

import pytest

from app.domain.enums import AppointmentStatus
from app.domain.exceptions import (
    ServiceInactive,
    ServiceNotFound,
    WindowNotAvailable,
    TimeConflict,
)
from app.domain.models import MasterSettings, WorkingHours
from app.domain.services.booking import BookingService
from tests.factories import (
    CLIENT_ID,
    MASTER_ID,
    OTHER_ID,
    make_appointment,
    make_repos,
    make_service,
)


# 08:00 MSK — before 09:00–12:00 grid
NOW = datetime(2026, 9, 10, 5, 0, tzinfo=timezone.utc)
CREATED = NOW


def _settings(**kwargs) -> MasterSettings:
    base = dict(
        master_user_id=MASTER_ID,
        timezone="Europe/Moscow",
        slot_step_minutes=None,
        gap_minutes=0,
        min_lead_minutes=0,
        booking_horizon_days=1,
        created_at=CREATED,
        updated_at=CREATED,
    )
    base.update(kwargs)
    return MasterSettings(**base)


def _thursday_morning() -> WorkingHours:
    return WorkingHours(
        id=1,
        master_user_id=MASTER_ID,
        weekday=4,
        starts_time=time(9, 0),
        ends_time=time(12, 0),
        created_at=CREATED,
    )


def _repos_with_schedule(**kwargs):
    return make_repos(
        services=kwargs.get("services", [make_service(duration_minutes=60)]),
        settings=kwargs.get("settings", _settings()),
        working_hours=kwargs.get("working_hours", [_thursday_morning()]),
        time_offs=kwargs.get("time_offs", []),
        appointments=kwargs.get("appointments", []),
    )


@pytest.mark.asyncio
async def test_book_window_creates_pending_appointment():
    booking = BookingService(_repos_with_schedule())
    starts = datetime(2026, 9, 10, 6, 0, tzinfo=timezone.utc)  # 09:00 MSK

    appointment = await booking.book_window(
        client_user_id=CLIENT_ID,
        service_id=1,
        starts_at=starts,
        now=NOW,
    )

    assert appointment.status == AppointmentStatus.PENDING
    assert appointment.starts_at == starts
    assert appointment.ends_at == datetime(2026, 9, 10, 7, 0, tzinfo=timezone.utc)


@pytest.mark.asyncio
async def test_book_window_rejects_unknown_service():
    booking = BookingService(_repos_with_schedule(services=[]))

    with pytest.raises(ServiceNotFound):
        await booking.book_window(
            client_user_id=CLIENT_ID,
            service_id=999,
            starts_at=datetime(2026, 9, 10, 6, 0, tzinfo=timezone.utc),
            now=NOW,
        )


@pytest.mark.asyncio
async def test_book_window_rejects_inactive_service():
    booking = BookingService(
        _repos_with_schedule(services=[make_service(is_active=False)]),
    )

    with pytest.raises(ServiceInactive):
        await booking.book_window(
            client_user_id=CLIENT_ID,
            service_id=1,
            starts_at=datetime(2026, 9, 10, 6, 0, tzinfo=timezone.utc),
            now=NOW,
        )


@pytest.mark.asyncio
async def test_book_window_rejects_time_not_in_grid():
    booking = BookingService(_repos_with_schedule())

    with pytest.raises(WindowNotAvailable):
        await booking.book_window(
            client_user_id=CLIENT_ID,
            service_id=1,
            starts_at=datetime(2026, 9, 10, 6, 30, tzinfo=timezone.utc),  # 09:30
            now=NOW,
        )


@pytest.mark.asyncio
async def test_book_window_rejects_when_already_taken():
    taken_start = datetime(2026, 9, 10, 6, 0, tzinfo=timezone.utc)
    taken_end = datetime(2026, 9, 10, 7, 0, tzinfo=timezone.utc)
    booking = BookingService(
        _repos_with_schedule(
            appointments=[
                make_appointment(
                    starts_at=taken_start,
                    ends_at=taken_end,
                ),
            ],
        ),
    )

    with pytest.raises(WindowNotAvailable):
        await booking.book_window(
            client_user_id=OTHER_ID,
            service_id=1,
            starts_at=taken_start,
            now=NOW,
        )


@pytest.mark.asyncio
async def test_list_available_windows_returns_grid():
    booking = BookingService(_repos_with_schedule())

    windows = await booking.list_available_windows(
        master_user_id=MASTER_ID,
        duration_minutes=60,
        now=NOW,
    )

    assert [w.starts_at for w in windows] == [
        datetime(2026, 9, 10, 6, 0, tzinfo=timezone.utc),
        datetime(2026, 9, 10, 7, 0, tzinfo=timezone.utc),
        datetime(2026, 9, 10, 8, 0, tzinfo=timezone.utc),
    ]
