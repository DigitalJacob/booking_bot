"""Unit tests for FakeAppointmentsRepository.reschedule contract."""

from datetime import UTC, datetime, timedelta

import pytest
from app.domain.enums import AppointmentStatus, RescheduleKind
from app.domain.exceptions import TimeConflict

from tests.factories import (
    CLIENT_ID,
    MASTER_ID,
    OTHER_ID,
    FakeAppointmentsRepository,
    make_appointment,
)

START = datetime(2026, 10, 15, 10, 0, tzinfo=UTC)
END = START + timedelta(hours=1)


@pytest.mark.asyncio
async def test_fake_reschedule_clears_reminders_and_sets_rescheduled_at():
    existing = make_appointment(
        starts_at=START,
        ends_at=END,
        status=AppointmentStatus.CONFIRMED,
        client_hour_reminded_at=START,
        master_evening_reminded_at=START,
    )
    repo = FakeAppointmentsRepository([existing])
    new_start = START + timedelta(hours=2)
    new_end = new_start + timedelta(hours=1)

    updated = await repo.reschedule(
        appointment_id=existing.id,
        starts_at=new_start,
        ends_at=new_end,
        status=AppointmentStatus.PENDING,
    )

    assert updated is not None
    assert updated.starts_at == new_start
    assert updated.status == AppointmentStatus.PENDING
    assert updated.rescheduled_at is not None
    assert updated.client_hour_reminded_at is None
    assert updated.master_evening_reminded_at is None


@pytest.mark.asyncio
async def test_fake_reschedule_overlap_raises_time_conflict():
    first = make_appointment(
        appointment_id=1,
        client_user_id=CLIENT_ID,
        starts_at=START,
        ends_at=END,
        status=AppointmentStatus.CONFIRMED,
    )
    second = make_appointment(
        appointment_id=2,
        client_user_id=OTHER_ID,
        starts_at=END,
        ends_at=END + timedelta(hours=1),
        status=AppointmentStatus.PENDING,
    )
    repo = FakeAppointmentsRepository([first, second])

    with pytest.raises(TimeConflict):
        await repo.reschedule(
            appointment_id=first.id,
            starts_at=START + timedelta(minutes=30),
            ends_at=END + timedelta(minutes=30),
            status=AppointmentStatus.CONFIRMED,
        )


@pytest.mark.asyncio
async def test_fake_reschedule_allows_overlap_with_self():
    existing = make_appointment(
        starts_at=START,
        ends_at=END,
        status=AppointmentStatus.CONFIRMED,
    )
    repo = FakeAppointmentsRepository([existing])
    shifted_start = START + timedelta(minutes=30)
    shifted_end = END + timedelta(minutes=30)

    updated = await repo.reschedule(
        appointment_id=existing.id,
        starts_at=shifted_start,
        ends_at=shifted_end,
        status=AppointmentStatus.CONFIRMED,
    )
    assert updated is not None
    assert updated.starts_at == shifted_start


@pytest.mark.asyncio
async def test_fake_add_reschedule_log():
    existing = make_appointment(starts_at=START, ends_at=END)
    repo = FakeAppointmentsRepository([existing])
    new_start = START + timedelta(hours=1)
    new_end = new_start + timedelta(hours=1)

    await repo.add_reschedule_log(
        appointment_id=existing.id,
        actor_user_id=MASTER_ID,
        kind=RescheduleKind.SHIFT,
        old_starts_at=START,
        old_ends_at=END,
        new_starts_at=new_start,
        new_ends_at=new_end,
    )

    assert len(repo.reschedule_logs) == 1
    assert repo.reschedule_logs[0]["kind"] == RescheduleKind.SHIFT
    assert repo.reschedule_logs[0]["actor_user_id"] == MASTER_ID
