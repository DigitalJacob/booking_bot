"""Unit tests for BookingService.reschedule and shift_late."""

from datetime import UTC, datetime, time, timedelta
from decimal import Decimal

import pytest
from app.domain.enums import AppointmentStatus, RescheduleKind
from app.domain.exceptions import (
    AppointmentAlreadyEnded,
    ForbiddenBookingAction,
    InvalidAppointmentStatus,
    RescheduleSameTime,
    RescheduleTooLate,
    WindowNotAvailable,
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
NOW = datetime(2026, 9, 10, 5, 0, tzinfo=UTC)
CREATED = NOW
SLOT_09 = datetime(2026, 9, 10, 6, 0, tzinfo=UTC)  # 09:00 MSK
SLOT_10 = datetime(2026, 9, 10, 7, 0, tzinfo=UTC)  # 10:00 MSK
SLOT_11 = datetime(2026, 9, 10, 8, 0, tzinfo=UTC)  # 11:00 MSK


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


def _repos(**kwargs):
    return make_repos(
        services=kwargs.get("services", [make_service(duration_minutes=60)]),
        settings=kwargs.get("settings", _settings()),
        working_hours=kwargs.get("working_hours", [_thursday_morning()]),
        time_offs=kwargs.get("time_offs", []),
        appointments=kwargs.get("appointments", []),
        manual_clients=kwargs.get("manual_clients", []),
    )


@pytest.mark.asyncio
async def test_master_reschedule_to_overlapping_neighbor_keeps_status():
    """Exclude self so a move onto a slot that overlaps the old time works."""
    repos = _repos(
        appointments=[
            make_appointment(
                appointment_id=1,
                starts_at=SLOT_09,
                ends_at=SLOT_10,
                status=AppointmentStatus.CONFIRMED,
                price_snapshot=Decimal("1500"),
            ),
        ],
    )
    booking = BookingService(repos)

    result = await booking.reschedule(
        appointment_id=1,
        actor_user_id=MASTER_ID,
        new_starts_at=SLOT_10,
        now=NOW,
    )

    assert result.appointment.starts_at == SLOT_10
    assert result.appointment.ends_at == SLOT_11
    assert result.appointment.status == AppointmentStatus.CONFIRMED
    assert result.old_starts_at == SLOT_09
    assert result.old_ends_at == SLOT_10
    assert result.appointment.price_snapshot == Decimal("1500")
    assert result.appointment.id == 1


@pytest.mark.asyncio
async def test_client_reschedule_sets_pending():
    repos = _repos(
        appointments=[
            make_appointment(
                appointment_id=1,
                starts_at=SLOT_09,
                ends_at=SLOT_10,
                status=AppointmentStatus.CONFIRMED,
            ),
        ],
    )
    booking = BookingService(repos)

    result = await booking.reschedule(
        appointment_id=1,
        actor_user_id=CLIENT_ID,
        new_starts_at=SLOT_10,
        now=NOW,
    )

    assert result.appointment.status == AppointmentStatus.PENDING
    assert result.appointment.starts_at == SLOT_10


@pytest.mark.asyncio
async def test_client_reschedule_inside_min_lead_raises():
    repos = _repos(
        settings=_settings(min_lead_minutes=120),
        appointments=[
            make_appointment(
                appointment_id=1,
                starts_at=SLOT_09,  # 1h after NOW → inside 120 min lead
                ends_at=SLOT_10,
                status=AppointmentStatus.CONFIRMED,
            ),
        ],
    )
    booking = BookingService(repos)

    with pytest.raises(RescheduleTooLate):
        await booking.reschedule(
            appointment_id=1,
            actor_user_id=CLIENT_ID,
            new_starts_at=SLOT_11,
            now=NOW,
        )


@pytest.mark.asyncio
async def test_master_reschedule_ignores_min_lead():
    repos = _repos(
        settings=_settings(min_lead_minutes=120),
        appointments=[
            make_appointment(
                appointment_id=1,
                starts_at=SLOT_09,
                ends_at=SLOT_10,
                status=AppointmentStatus.PENDING,
            ),
        ],
    )
    booking = BookingService(repos)

    result = await booking.reschedule(
        appointment_id=1,
        actor_user_id=MASTER_ID,
        new_starts_at=SLOT_10,
        now=NOW,
    )

    assert result.appointment.starts_at == SLOT_10
    assert result.appointment.status == AppointmentStatus.PENDING


@pytest.mark.asyncio
async def test_reschedule_same_time_raises():
    repos = _repos(
        appointments=[
            make_appointment(
                appointment_id=1,
                starts_at=SLOT_09,
                ends_at=SLOT_10,
            ),
        ],
    )
    booking = BookingService(repos)

    with pytest.raises(RescheduleSameTime):
        await booking.reschedule(
            appointment_id=1,
            actor_user_id=MASTER_ID,
            new_starts_at=SLOT_09,
            now=NOW,
        )


@pytest.mark.asyncio
async def test_reschedule_foreign_actor_forbidden():
    repos = _repos(
        appointments=[
            make_appointment(
                appointment_id=1,
                starts_at=SLOT_09,
                ends_at=SLOT_10,
            ),
        ],
    )
    booking = BookingService(repos)

    with pytest.raises(ForbiddenBookingAction):
        await booking.reschedule(
            appointment_id=1,
            actor_user_id=OTHER_ID,
            new_starts_at=SLOT_10,
            now=NOW,
        )


@pytest.mark.asyncio
async def test_manual_appointment_client_cannot_reschedule():
    repos = _repos(
        appointments=[
            make_appointment(
                appointment_id=1,
                client_user_id=None,
                manual_client_id=1,
                starts_at=SLOT_09,
                ends_at=SLOT_10,
                status=AppointmentStatus.CONFIRMED,
            ),
        ],
    )
    booking = BookingService(repos)

    with pytest.raises(ForbiddenBookingAction):
        await booking.reschedule(
            appointment_id=1,
            actor_user_id=CLIENT_ID,
            new_starts_at=SLOT_10,
            now=NOW,
        )

    result = await booking.reschedule(
        appointment_id=1,
        actor_user_id=MASTER_ID,
        new_starts_at=SLOT_10,
        now=NOW,
    )
    assert result.appointment.starts_at == SLOT_10


@pytest.mark.asyncio
async def test_reschedule_ended_appointment_raises():
    past_start = NOW - timedelta(hours=3)
    past_end = NOW - timedelta(hours=2)
    repos = _repos(
        appointments=[
            make_appointment(
                appointment_id=1,
                starts_at=past_start,
                ends_at=past_end,
                status=AppointmentStatus.CONFIRMED,
            ),
        ],
    )
    booking = BookingService(repos)

    with pytest.raises(AppointmentAlreadyEnded):
        await booking.reschedule(
            appointment_id=1,
            actor_user_id=MASTER_ID,
            new_starts_at=SLOT_10,
            now=NOW,
        )


@pytest.mark.asyncio
async def test_reschedule_cancelled_raises():
    repos = _repos(
        appointments=[
            make_appointment(
                appointment_id=1,
                starts_at=SLOT_09,
                ends_at=SLOT_10,
                status=AppointmentStatus.CANCELLED,
            ),
        ],
    )
    booking = BookingService(repos)

    with pytest.raises(InvalidAppointmentStatus):
        await booking.reschedule(
            appointment_id=1,
            actor_user_id=MASTER_ID,
            new_starts_at=SLOT_10,
            now=NOW,
        )


@pytest.mark.asyncio
async def test_reschedule_clears_reminders_and_logs_move():
    reminded = NOW - timedelta(hours=1)
    repos = _repos(
        appointments=[
            make_appointment(
                appointment_id=1,
                starts_at=SLOT_09,
                ends_at=SLOT_10,
                status=AppointmentStatus.CONFIRMED,
                client_evening_reminded_at=reminded,
                client_hour_reminded_at=reminded,
                master_evening_reminded_at=reminded,
                master_hour_reminded_at=reminded,
            ),
        ],
    )
    booking = BookingService(repos)

    result = await booking.reschedule(
        appointment_id=1,
        actor_user_id=MASTER_ID,
        new_starts_at=SLOT_11,
        now=NOW,
    )

    updated = result.appointment
    assert updated.client_evening_reminded_at is None
    assert updated.client_hour_reminded_at is None
    assert updated.master_evening_reminded_at is None
    assert updated.master_hour_reminded_at is None
    assert updated.rescheduled_at is not None
    assert len(repos.appointments.reschedule_logs) == 1
    log = repos.appointments.reschedule_logs[0]
    assert log["kind"] == RescheduleKind.MOVE
    assert log["actor_user_id"] == MASTER_ID
    assert log["old_starts_at"] == SLOT_09
    assert log["new_starts_at"] == SLOT_11


@pytest.mark.asyncio
async def test_reschedule_uses_appointment_duration_not_service():
    """Duration comes from the appointment even if the service length changed."""
    repos = _repos(
        services=[make_service(duration_minutes=30)],
        appointments=[
            make_appointment(
                appointment_id=1,
                starts_at=SLOT_09,
                ends_at=SLOT_10,  # 60 min snapshot
                status=AppointmentStatus.CONFIRMED,
            ),
        ],
    )
    booking = BookingService(repos)

    result = await booking.reschedule(
        appointment_id=1,
        actor_user_id=MASTER_ID,
        new_starts_at=SLOT_10,
        now=NOW,
    )

    assert result.appointment.ends_at == SLOT_11


@pytest.mark.asyncio
async def test_shift_late_ok_inside_work_hours():
    repos = _repos(
        appointments=[
            make_appointment(
                appointment_id=1,
                starts_at=SLOT_09,
                ends_at=SLOT_10,
                status=AppointmentStatus.CONFIRMED,
            ),
        ],
    )
    booking = BookingService(repos)

    result = await booking.shift_late(
        appointment_id=1,
        master_user_id=MASTER_ID,
        minutes=15,
        now=NOW,
    )

    assert result.appointment.starts_at == SLOT_09 + timedelta(minutes=15)
    assert result.appointment.ends_at == SLOT_10 + timedelta(minutes=15)
    assert result.appointment.status == AppointmentStatus.CONFIRMED
    assert repos.appointments.reschedule_logs[0]["kind"] == RescheduleKind.SHIFT


@pytest.mark.asyncio
async def test_shift_late_past_work_day_end_raises():
    # 11:00–12:00 +30 → ends 12:30, past close at 12:00
    repos = _repos(
        appointments=[
            make_appointment(
                appointment_id=1,
                starts_at=SLOT_11,
                ends_at=SLOT_11 + timedelta(hours=1),
                status=AppointmentStatus.CONFIRMED,
            ),
        ],
    )
    booking = BookingService(repos)

    with pytest.raises(WindowNotAvailable):
        await booking.shift_late(
            appointment_id=1,
            master_user_id=MASTER_ID,
            minutes=30,
            now=NOW,
        )


@pytest.mark.asyncio
async def test_shift_late_gap_into_next_appointment_raises():
    next_start = SLOT_10 + timedelta(minutes=15)  # 10:15 MSK
    repos = _repos(
        settings=_settings(gap_minutes=15),
        appointments=[
            make_appointment(
                appointment_id=1,
                starts_at=SLOT_09,
                ends_at=SLOT_10,
                status=AppointmentStatus.CONFIRMED,
            ),
            make_appointment(
                appointment_id=2,
                starts_at=next_start,
                ends_at=next_start + timedelta(hours=1),
                status=AppointmentStatus.PENDING,
            ),
        ],
    )
    booking = BookingService(repos)

    with pytest.raises(WindowNotAvailable):
        await booking.shift_late(
            appointment_id=1,
            master_user_id=MASTER_ID,
            minutes=30,  # 09:30–10:30 overlaps next (+gap) at 10:15
            now=NOW,
        )


@pytest.mark.asyncio
async def test_shift_late_foreign_master_forbidden():
    repos = _repos(
        appointments=[
            make_appointment(
                appointment_id=1,
                starts_at=SLOT_09,
                ends_at=SLOT_10,
            ),
        ],
    )
    booking = BookingService(repos)

    with pytest.raises(ForbiddenBookingAction):
        await booking.shift_late(
            appointment_id=1,
            master_user_id=OTHER_ID,
            minutes=15,
            now=NOW,
        )


@pytest.mark.asyncio
async def test_shift_late_invalid_minutes_raises():
    repos = _repos(
        appointments=[
            make_appointment(
                appointment_id=1,
                starts_at=SLOT_09,
                ends_at=SLOT_10,
            ),
        ],
    )
    booking = BookingService(repos)

    with pytest.raises(ValueError):
        await booking.shift_late(
            appointment_id=1,
            master_user_id=MASTER_ID,
            minutes=0,
            now=NOW,
        )
