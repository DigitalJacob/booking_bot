from datetime import UTC, datetime, time
from decimal import Decimal

import pytest
from app.domain.enums import AppointmentStatus
from app.domain.exceptions import (
    ForbiddenBookingAction,
    InvalidAppointmentClient,
    ManualClientNotFound,
    ServiceInactive,
    ServiceNotFound,
    WindowNotAvailable,
)
from app.domain.models import MasterSettings, WorkingHours
from app.domain.services.booking import BookingService

from tests.factories import (
    CLIENT_ID,
    MASTER_ID,
    OTHER_ID,
    make_appointment,
    make_manual_client,
    make_repos,
    make_service,
)

# 08:00 MSK — before 09:00–12:00 grid
NOW = datetime(2026, 9, 10, 5, 0, tzinfo=UTC)
CREATED = NOW


def _settings(**kwargs) -> MasterSettings:
    base = {
        "master_user_id": MASTER_ID,
        "timezone": "Europe/Moscow",
        "slot_step_minutes": None,
        "gap_minutes": 0,
        "min_lead_minutes": 0,
        "booking_horizon_days": 1,
        "created_at": CREATED,
        "updated_at": CREATED,
    }
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
        manual_clients=kwargs.get("manual_clients", []),
    )


@pytest.mark.asyncio
async def test_book_window_creates_pending_appointment():
    booking = BookingService(_repos_with_schedule())
    starts = datetime(2026, 9, 10, 6, 0, tzinfo=UTC)  # 09:00 MSK

    appointment = await booking.book_window(
        client_user_id=CLIENT_ID,
        service_id=1,
        starts_at=starts,
        now=NOW,
    )

    assert appointment.status == AppointmentStatus.PENDING
    assert appointment.starts_at == starts
    assert appointment.ends_at == datetime(2026, 9, 10, 7, 0, tzinfo=UTC)


@pytest.mark.asyncio
async def test_book_window_stores_service_price_snapshot():
    booking = BookingService(
        _repos_with_schedule(services=[make_service(price=Decimal("2500.50"))]),
    )

    appointment = await booking.book_window(
        client_user_id=CLIENT_ID,
        service_id=1,
        starts_at=datetime(2026, 9, 10, 6, 0, tzinfo=UTC),
        now=NOW,
    )

    assert appointment.price_snapshot == Decimal("2500.50")


@pytest.mark.asyncio
async def test_book_window_stores_empty_snapshot_for_unpriced_service():
    booking = BookingService(
        _repos_with_schedule(services=[make_service(price=None)]),
    )

    appointment = await booking.book_window(
        client_user_id=CLIENT_ID,
        service_id=1,
        starts_at=datetime(2026, 9, 10, 6, 0, tzinfo=UTC),
        now=NOW,
    )

    assert appointment.price_snapshot is None


@pytest.mark.asyncio
async def test_book_window_rejects_unknown_service():
    booking = BookingService(_repos_with_schedule(services=[]))

    with pytest.raises(ServiceNotFound):
        await booking.book_window(
            client_user_id=CLIENT_ID,
            service_id=999,
            starts_at=datetime(2026, 9, 10, 6, 0, tzinfo=UTC),
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
            starts_at=datetime(2026, 9, 10, 6, 0, tzinfo=UTC),
            now=NOW,
        )


@pytest.mark.asyncio
async def test_book_window_rejects_time_not_in_grid():
    booking = BookingService(_repos_with_schedule())

    with pytest.raises(WindowNotAvailable):
        await booking.book_window(
            client_user_id=CLIENT_ID,
            service_id=1,
            starts_at=datetime(2026, 9, 10, 6, 30, tzinfo=UTC),  # 09:30
            now=NOW,
        )


@pytest.mark.asyncio
async def test_book_window_rejects_when_already_taken():
    taken_start = datetime(2026, 9, 10, 6, 0, tzinfo=UTC)
    taken_end = datetime(2026, 9, 10, 7, 0, tzinfo=UTC)
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
        datetime(2026, 9, 10, 6, 0, tzinfo=UTC),
        datetime(2026, 9, 10, 7, 0, tzinfo=UTC),
        datetime(2026, 9, 10, 8, 0, tzinfo=UTC),
    ]


@pytest.mark.asyncio
async def test_book_for_client_creates_confirmed_appointment():
    booking = BookingService(_repos_with_schedule())
    starts = datetime(2026, 9, 10, 6, 0, tzinfo=UTC)

    appointment = await booking.book_for_client(
        master_user_id=MASTER_ID,
        client_user_id=CLIENT_ID,
        service_id=1,
        starts_at=starts,
        now=NOW,
    )

    assert appointment.status == AppointmentStatus.CONFIRMED
    assert appointment.client_user_id == CLIENT_ID
    assert appointment.master_user_id == MASTER_ID
    assert appointment.starts_at == starts
    assert appointment.price_snapshot == Decimal("1500")


@pytest.mark.asyncio
async def test_book_for_client_rejects_other_masters_service():
    booking = BookingService(
        _repos_with_schedule(
            services=[make_service(master_user_id=OTHER_ID)],
        ),
    )

    with pytest.raises(ForbiddenBookingAction):
        await booking.book_for_client(
            master_user_id=MASTER_ID,
            client_user_id=CLIENT_ID,
            service_id=1,
            starts_at=datetime(2026, 9, 10, 6, 0, tzinfo=UTC),
            now=NOW,
        )


@pytest.mark.asyncio
async def test_book_for_client_rejects_when_already_taken():
    taken_start = datetime(2026, 9, 10, 6, 0, tzinfo=UTC)
    booking = BookingService(
        _repos_with_schedule(
            appointments=[
                make_appointment(
                    starts_at=taken_start,
                    ends_at=datetime(2026, 9, 10, 7, 0, tzinfo=UTC),
                ),
            ],
        ),
    )

    with pytest.raises(WindowNotAvailable):
        await booking.book_for_client(
            master_user_id=MASTER_ID,
            client_user_id=OTHER_ID,
            service_id=1,
            starts_at=taken_start,
            now=NOW,
        )


@pytest.mark.asyncio
async def test_book_for_client_ignores_min_lead_but_keeps_horizon():
    """Client cannot book the first slot under min_lead; master can.

    Horizon still applies: a start outside booking_horizon_days is rejected.
    """
    starts_near = datetime(2026, 9, 10, 6, 0, tzinfo=UTC)  # 09:00 MSK
    repos = _repos_with_schedule(
        settings=_settings(min_lead_minutes=120, booking_horizon_days=1),
    )
    booking = BookingService(repos)

    with pytest.raises(WindowNotAvailable):
        await booking.book_window(
            client_user_id=CLIENT_ID,
            service_id=1,
            starts_at=starts_near,
            now=NOW,
        )

    appointment = await booking.book_for_client(
        master_user_id=MASTER_ID,
        client_user_id=CLIENT_ID,
        service_id=1,
        starts_at=starts_near,
        now=NOW,
    )
    assert appointment.status == AppointmentStatus.CONFIRMED

    with pytest.raises(WindowNotAvailable):
        await booking.book_for_client(
            master_user_id=MASTER_ID,
            client_user_id=OTHER_ID,
            service_id=1,
            starts_at=datetime(2026, 9, 12, 6, 0, tzinfo=UTC),
            now=NOW,
        )


@pytest.mark.asyncio
async def test_book_for_client_with_manual_client():
    manual = make_manual_client()
    booking = BookingService(_repos_with_schedule(manual_clients=[manual]))
    starts = datetime(2026, 9, 10, 6, 0, tzinfo=UTC)

    appointment = await booking.book_for_client(
        master_user_id=MASTER_ID,
        manual_client_id=manual.id,
        service_id=1,
        starts_at=starts,
        now=NOW,
    )

    assert appointment.status == AppointmentStatus.CONFIRMED
    assert appointment.client_user_id is None
    assert appointment.manual_client_id == manual.id
    assert appointment.price_snapshot == Decimal("1500")


@pytest.mark.asyncio
async def test_book_for_client_reuses_manual_client_on_rebook():
    """Second booking for the same walk-in keeps the same manual_client_id."""
    manual = make_manual_client()
    booking = BookingService(_repos_with_schedule(manual_clients=[manual]))
    first_starts = datetime(2026, 9, 10, 6, 0, tzinfo=UTC)
    second_starts = datetime(2026, 9, 10, 7, 0, tzinfo=UTC)

    first = await booking.book_for_client(
        master_user_id=MASTER_ID,
        manual_client_id=manual.id,
        service_id=1,
        starts_at=first_starts,
        now=NOW,
    )
    second = await booking.book_for_client(
        master_user_id=MASTER_ID,
        manual_client_id=manual.id,
        service_id=1,
        starts_at=second_starts,
        now=NOW,
    )

    assert first.id != second.id
    assert first.manual_client_id == manual.id
    assert second.manual_client_id == manual.id
    assert first.client_user_id is None
    assert second.client_user_id is None


@pytest.mark.asyncio
async def test_book_for_client_rejects_unknown_manual_client():
    booking = BookingService(_repos_with_schedule())

    with pytest.raises(ManualClientNotFound):
        await booking.book_for_client(
            master_user_id=MASTER_ID,
            manual_client_id=999,
            service_id=1,
            starts_at=datetime(2026, 9, 10, 6, 0, tzinfo=UTC),
            now=NOW,
        )


@pytest.mark.asyncio
async def test_book_for_client_rejects_manual_of_other_master():
    manual = make_manual_client(master_user_id=OTHER_ID)
    booking = BookingService(_repos_with_schedule(manual_clients=[manual]))

    with pytest.raises(ManualClientNotFound):
        await booking.book_for_client(
            master_user_id=MASTER_ID,
            manual_client_id=manual.id,
            service_id=1,
            starts_at=datetime(2026, 9, 10, 6, 0, tzinfo=UTC),
            now=NOW,
        )


@pytest.mark.asyncio
async def test_book_for_client_requires_exactly_one_client_ref():
    booking = BookingService(_repos_with_schedule())
    starts = datetime(2026, 9, 10, 6, 0, tzinfo=UTC)

    with pytest.raises(InvalidAppointmentClient):
        await booking.book_for_client(
            master_user_id=MASTER_ID,
            service_id=1,
            starts_at=starts,
            now=NOW,
        )

    with pytest.raises(InvalidAppointmentClient):
        await booking.book_for_client(
            master_user_id=MASTER_ID,
            client_user_id=CLIENT_ID,
            manual_client_id=1,
            service_id=1,
            starts_at=starts,
            now=NOW,
        )
