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
async def test_price_snapshot_round_trips(repos: Repositories) -> None:
    service = await _seed_service(repos)

    created = await repos.appointments.add_appointment(
        client_user_id=CLIENT_ID,
        master_user_id=MASTER_ID,
        service_id=service.id,
        starts_at=START,
        ends_at=END,
        price_snapshot=Decimal("2000.00"),
    )
    loaded = await repos.appointments.get_appointment(appointment_id=created.id)

    assert created.price_snapshot == Decimal("2000.00")
    assert loaded is not None
    assert loaded.price_snapshot == Decimal("2000.00")


@pytest.mark.asyncio
async def test_price_snapshot_defaults_to_null(repos: Repositories) -> None:
    service = await _seed_service(repos)

    created = await repos.appointments.add_appointment(
        client_user_id=CLIENT_ID,
        master_user_id=MASTER_ID,
        service_id=service.id,
        starts_at=START,
        ends_at=END,
    )

    assert created.price_snapshot is None


@pytest.mark.asyncio
async def test_add_appointment_with_manual_client(repos: Repositories) -> None:
    from app.bot.utils.phone import normalize_phone, phone_digits
    from app.domain.exceptions import InvalidAppointmentClient

    service = await _seed_service(repos)
    phone = normalize_phone("+7 999 000-11-22")
    assert phone is not None
    manual = await repos.manual_clients.create(
        master_user_id=MASTER_ID,
        name="Walk-in",
        phone=phone,
        phone_digits=phone_digits(phone),
    )

    created = await repos.appointments.add_appointment(
        master_user_id=MASTER_ID,
        service_id=service.id,
        starts_at=START,
        ends_at=END,
        manual_client_id=manual.id,
        status=AppointmentStatus.CONFIRMED,
    )
    loaded = await repos.appointments.get_appointment(appointment_id=created.id)

    assert created.client_user_id is None
    assert created.manual_client_id == manual.id
    assert loaded is not None
    assert loaded.manual_client_id == manual.id

    with pytest.raises(InvalidAppointmentClient):
        await repos.appointments.add_appointment(
            master_user_id=MASTER_ID,
            service_id=service.id,
            starts_at=END,
            ends_at=END + timedelta(hours=1),
        )


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
