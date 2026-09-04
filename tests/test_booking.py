import pytest

from app.domain.enums import AppointmentStatus
from app.domain.exceptions import (
    ForbiddenBookingAction,
    InvalidAppointmentStatus,
    ServiceInactive,
    ServiceNotFound,
    SlotInThePast,
    SlotMasterMismatch,
    SlotNotFound,
    SlotTaken,
    SlotTooShort,
)
from app.domain.services.booking import BookingService
from tests.factories import (
    CLIENT_ID,
    MASTER_ID,
    NOW,
    OTHER_ID,
    make_appointment,
    make_repos,
    make_service,
    make_slot,
)


async def test_book_creates_pending_appointment():
    repos = make_repos(
        services=[make_service(duration_minutes=60)],
        slots=[make_slot(duration_minutes=90)],
    )
    booking = BookingService(repos)

    appointment = await booking.book(
        client_user_id=CLIENT_ID,
        service_id=1,
        slot_id=1,
        now=NOW,
    )

    assert appointment.client_user_id == CLIENT_ID
    assert appointment.master_user_id == MASTER_ID
    assert appointment.status == AppointmentStatus.PENDING


async def test_book_allows_slot_exactly_matching_service_duration():
    repos = make_repos(
        services=[make_service(duration_minutes=60)],
        slots=[make_slot(duration_minutes=60)],
    )
    booking = BookingService(repos)

    appointment = await booking.book(
        client_user_id=CLIENT_ID,
        service_id=1,
        slot_id=1,
        now=NOW,
    )

    assert appointment.status == AppointmentStatus.PENDING


async def test_book_rejects_slot_shorter_than_service():
    repos = make_repos(
        services=[make_service(duration_minutes=60)],
        slots=[make_slot(duration_minutes=59)],
    )
    booking = BookingService(repos)

    with pytest.raises(SlotTooShort):
        await booking.book(
            client_user_id=CLIENT_ID,
            service_id=1,
            slot_id=1,
            now=NOW,
        )


async def test_book_rejects_unknown_service():
    repos = make_repos(slots=[make_slot()])
    booking = BookingService(repos)

    with pytest.raises(ServiceNotFound):
        await booking.book(
            client_user_id=CLIENT_ID,
            service_id=999,
            slot_id=1,
            now=NOW,
        )


async def test_book_rejects_inactive_service():
    repos = make_repos(
        services=[make_service(is_active=False)],
        slots=[make_slot()],
    )
    booking = BookingService(repos)

    with pytest.raises(ServiceInactive):
        await booking.book(
            client_user_id=CLIENT_ID,
            service_id=1,
            slot_id=1,
            now=NOW,
        )


async def test_book_rejects_unknown_slot():
    repos = make_repos(services=[make_service()])
    booking = BookingService(repos)

    with pytest.raises(SlotNotFound):
        await booking.book(
            client_user_id=CLIENT_ID,
            service_id=1,
            slot_id=999,
            now=NOW,
        )


async def test_book_rejects_slot_of_another_master():
    repos = make_repos(
        services=[make_service(master_user_id=MASTER_ID)],
        slots=[make_slot(master_user_id=OTHER_ID)],
    )
    booking = BookingService(repos)

    with pytest.raises(SlotMasterMismatch):
        await booking.book(
            client_user_id=CLIENT_ID,
            service_id=1,
            slot_id=1,
            now=NOW,
        )


async def test_book_rejects_slot_in_the_past():
    repos = make_repos(
        services=[make_service()],
        slots=[make_slot(starts_in_hours=-2)],
    )
    booking = BookingService(repos)

    with pytest.raises(SlotInThePast):
        await booking.book(
            client_user_id=CLIENT_ID,
            service_id=1,
            slot_id=1,
            now=NOW,
        )


async def test_book_rejects_already_taken_slot():
    repos = make_repos(
        services=[make_service()],
        slots=[make_slot()],
        appointments=[make_appointment(slot_id=1)],
    )
    booking = BookingService(repos)

    with pytest.raises(SlotTaken):
        await booking.book(
            client_user_id=OTHER_ID,
            service_id=1,
            slot_id=1,
            now=NOW,
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


async def test_list_available_slots_skips_slots_shorter_than_service():
    repos = make_repos(
        slots=[
            make_slot(slot_id=1, starts_in_hours=1, duration_minutes=30),
            make_slot(slot_id=2, starts_in_hours=3, duration_minutes=60),
            make_slot(slot_id=3, starts_in_hours=5, duration_minutes=120),
        ],
    )
    booking = BookingService(repos)

    slots = await booking.list_available_slots(
        master_user_id=MASTER_ID,
        now=NOW,
        min_duration_minutes=60,
    )

    assert [slot.id for slot in slots] == [2, 3]


async def test_list_client_appointments_excludes_cancelled():
    repos = make_repos(
        slots=[
            make_slot(slot_id=1, starts_in_hours=2),
            make_slot(slot_id=2, starts_in_hours=4),
        ],
        appointments=[
            make_appointment(appointment_id=1, slot_id=1),
            make_appointment(
                appointment_id=2,
                slot_id=2,
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
    repos = make_repos(
        slots=[
            make_slot(slot_id=1, starts_in_hours=-3),
            make_slot(slot_id=2, starts_in_hours=3),
        ],
        appointments=[
            make_appointment(appointment_id=1, slot_id=1),
            make_appointment(appointment_id=2, slot_id=2),
        ],
    )
    booking = BookingService(repos)

    result = await booking.list_client_appointments(
        client_user_id=CLIENT_ID,
        now=NOW,
    )

    assert [item.id for item in result] == [2]
