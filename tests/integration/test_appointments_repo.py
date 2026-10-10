from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from app.domain.enums import AppointmentStatus, UserRole
from app.domain.exceptions import TimeConflict
from app.domain.models import Service
from app.infrastructure.database.repositories import Repositories

pytestmark = pytest.mark.integration

MASTER_ID = 1001
CLIENT_ID = 2001
OTHER_CLIENT_ID = 2002

START = datetime(2026, 10, 15, 10, 0, tzinfo=UTC)
END = START + timedelta(hours=1)


async def _seed_service(repos: Repositories) -> Service:
    await repos.users.add_user(
        user_id=MASTER_ID,
        language="ru",
        role=UserRole.MASTER,
    )
    await repos.users.add_user(
        user_id=CLIENT_ID,
        language="ru",
        role=UserRole.CLIENT,
    )
    await repos.users.add_user(
        user_id=OTHER_CLIENT_ID,
        language="ru",
        role=UserRole.CLIENT,
    )
    return await repos.services.add_service(
        master_user_id=MASTER_ID,
        title="Integration massage",
        duration_minutes=60,
        price=Decimal("2000.00"),
    )


@pytest.mark.asyncio
async def test_overlapping_pending_raises_time_conflict(
        repos: Repositories,
) -> None:
    service = await _seed_service(repos)

    first = await repos.appointments.add_appointment(
        client_user_id=CLIENT_ID,
        master_user_id=MASTER_ID,
        service_id=service.id,
        starts_at=START,
        ends_at=END,
        status=AppointmentStatus.PENDING,
    )
    assert first.id > 0

    with pytest.raises(TimeConflict):
        await repos.appointments.add_appointment(
            client_user_id=OTHER_CLIENT_ID,
            master_user_id=MASTER_ID,
            service_id=service.id,
            starts_at=START + timedelta(minutes=30),
            ends_at=END + timedelta(minutes=30),
            status=AppointmentStatus.PENDING,
        )


@pytest.mark.asyncio
async def test_non_overlapping_appointments_ok(repos: Repositories) -> None:
    service = await _seed_service(repos)

    first = await repos.appointments.add_appointment(
        client_user_id=CLIENT_ID,
        master_user_id=MASTER_ID,
        service_id=service.id,
        starts_at=START,
        ends_at=END,
    )
    second = await repos.appointments.add_appointment(
        client_user_id=OTHER_CLIENT_ID,
        master_user_id=MASTER_ID,
        service_id=service.id,
        starts_at=END,
        ends_at=END + timedelta(hours=1),
    )
    assert second.id != first.id


@pytest.mark.asyncio
async def test_cancelled_slot_can_be_rebooked(repos: Repositories) -> None:
    service = await _seed_service(repos)

    original = await repos.appointments.add_appointment(
        client_user_id=CLIENT_ID,
        master_user_id=MASTER_ID,
        service_id=service.id,
        starts_at=START,
        ends_at=END,
        status=AppointmentStatus.PENDING,
    )
    cancelled = await repos.appointments.change_status(
        appointment_id=original.id,
        status=AppointmentStatus.CANCELLED,
    )
    assert cancelled is not None
    assert cancelled.status == AppointmentStatus.CANCELLED

    rebooked = await repos.appointments.add_appointment(
        client_user_id=OTHER_CLIENT_ID,
        master_user_id=MASTER_ID,
        service_id=service.id,
        starts_at=START,
        ends_at=END,
        status=AppointmentStatus.PENDING,
    )
    assert rebooked.id != original.id
