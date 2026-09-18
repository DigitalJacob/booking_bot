from datetime import timedelta

import pytest

from app.domain.enums import AppointmentStatus
from app.domain.exceptions import (
    ForbiddenBookingAction,
    InvalidAppointmentStatus,
)
from app.domain.services.booking import BookingService
from tests.factories import (
    CLIENT_ID,
    MASTER_ID,
    NOW,
    OTHER_ID,
    make_appointment,
    make_repos,
)


async def test_confirm_marks_appointment_confirmed():
    repos = make_repos(appointments=[make_appointment()])
    booking = BookingService(repos)

    updated = await booking.confirm(appointment_id=1, master_user_id=MASTER_ID)

    assert updated.status == AppointmentStatus.CONFIRMED


async def test_confirm_rejects_another_master():
    repos = make_repos(appointments=[make_appointment()])
    booking = BookingService(repos)

    with pytest.raises(ForbiddenBookingAction):
        await booking.confirm(appointment_id=1, master_user_id=OTHER_ID)


async def test_confirm_rejects_already_confirmed():
    repos = make_repos(
        appointments=[make_appointment(status=AppointmentStatus.CONFIRMED)],
    )
    booking = BookingService(repos)

    with pytest.raises(InvalidAppointmentStatus):
        await booking.confirm(appointment_id=1, master_user_id=MASTER_ID)


@pytest.mark.parametrize("actor_user_id", [CLIENT_ID, MASTER_ID])
async def test_cancel_allowed_for_client_and_master(actor_user_id):
    repos = make_repos(appointments=[make_appointment()])
    booking = BookingService(repos)

    updated = await booking.cancel(
        appointment_id=1,
        actor_user_id=actor_user_id,
    )

    assert updated.status == AppointmentStatus.CANCELLED


async def test_cancel_rejects_unrelated_user():
    repos = make_repos(appointments=[make_appointment()])
    booking = BookingService(repos)

    with pytest.raises(ForbiddenBookingAction):
        await booking.cancel(appointment_id=1, actor_user_id=OTHER_ID)


async def test_cancel_rejects_already_cancelled():
    repos = make_repos(
        appointments=[make_appointment(status=AppointmentStatus.CANCELLED)],
    )
    booking = BookingService(repos)

    with pytest.raises(InvalidAppointmentStatus):
        await booking.cancel(appointment_id=1, actor_user_id=CLIENT_ID)


async def test_list_client_appointments_excludes_cancelled():
    repos = make_repos(
        appointments=[
            make_appointment(appointment_id=1),
            make_appointment(
                appointment_id=2,
                status=AppointmentStatus.CANCELLED,
            ),
        ],
    )
    booking = BookingService(repos)
    result = await booking.list_client_appointments(
        client_user_id=CLIENT_ID,
        now=NOW,
    )
    assert [item.id for item in result] == [1]


async def test_list_client_appointments_excludes_past():
    past_start = NOW + timedelta(hours=-3)
    past_end = past_start + timedelta(minutes=60)
    future_start = NOW + timedelta(hours=3)
    future_end = future_start + timedelta(minutes=60)
    repos = make_repos(
        appointments=[
            make_appointment(
                appointment_id=1,
                starts_at=past_start,
                ends_at=past_end,
            ),
            make_appointment(
                appointment_id=2,
                starts_at=future_start,
                ends_at=future_end,
            ),
        ],
    )
    booking = BookingService(repos)
    result = await booking.list_client_appointments(
        client_user_id=CLIENT_ID,
        now=NOW,
    )
    assert [item.id for item in result] == [2]
