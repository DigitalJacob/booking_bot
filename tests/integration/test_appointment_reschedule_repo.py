from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from app.domain.enums import AppointmentStatus, ReminderKind, RescheduleKind, UserRole
from app.domain.exceptions import TimeConflict
from app.domain.models import Service
from app.infrastructure.database.repositories import Repositories
from psycopg.rows import dict_row

pytestmark = pytest.mark.integration

MASTER_ID = 1001
CLIENT_ID = 2001
OTHER_CLIENT_ID = 2002

START = datetime(2026, 10, 15, 10, 0, tzinfo=UTC)
END = START + timedelta(hours=1)
NEW_START = START + timedelta(hours=3)
NEW_END = NEW_START + timedelta(hours=1)


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
async def test_reschedule_updates_time_clears_reminders_and_logs(
    repos: Repositories,
    db_conn,
) -> None:
    service = await _seed_service(repos)
    created = await repos.appointments.add_appointment(
        client_user_id=CLIENT_ID,
        master_user_id=MASTER_ID,
        service_id=service.id,
        starts_at=START,
        ends_at=END,
        status=AppointmentStatus.CONFIRMED,
    )
    await repos.appointments.mark_reminder_sent(
        appointment_id=created.id,
        kind=ReminderKind.CLIENT_HOUR,
    )
    await repos.appointments.mark_reminder_sent(
        appointment_id=created.id,
        kind=ReminderKind.MASTER_EVENING,
    )

    updated = await repos.appointments.reschedule(
        appointment_id=created.id,
        starts_at=NEW_START,
        ends_at=NEW_END,
        status=AppointmentStatus.PENDING,
    )
    assert updated is not None
    assert updated.starts_at == NEW_START
    assert updated.ends_at == NEW_END
    assert updated.status == AppointmentStatus.PENDING
    assert updated.rescheduled_at is not None
    assert updated.client_hour_reminded_at is None
    assert updated.master_evening_reminded_at is None

    await repos.appointments.add_reschedule_log(
        appointment_id=created.id,
        actor_user_id=CLIENT_ID,
        kind=RescheduleKind.MOVE,
        old_starts_at=START,
        old_ends_at=END,
        new_starts_at=NEW_START,
        new_ends_at=NEW_END,
    )

    async with db_conn.cursor(row_factory=dict_row) as cursor:
        await cursor.execute(
            """
            SELECT kind, actor_user_id, old_starts_at, new_starts_at
            FROM appointment_reschedules
            WHERE appointment_id = %s;
            """,
            (created.id,),
        )
        row = await cursor.fetchone()
    assert row is not None
    assert row["kind"] == "move"
    assert row["actor_user_id"] == CLIENT_ID
    assert row["old_starts_at"] == START
    assert row["new_starts_at"] == NEW_START


@pytest.mark.asyncio
async def test_reschedule_overlap_raises_time_conflict(repos: Repositories) -> None:
    service = await _seed_service(repos)
    first = await repos.appointments.add_appointment(
        client_user_id=CLIENT_ID,
        master_user_id=MASTER_ID,
        service_id=service.id,
        starts_at=START,
        ends_at=END,
        status=AppointmentStatus.CONFIRMED,
    )
    await repos.appointments.add_appointment(
        client_user_id=OTHER_CLIENT_ID,
        master_user_id=MASTER_ID,
        service_id=service.id,
        starts_at=END,
        ends_at=END + timedelta(hours=1),
        status=AppointmentStatus.PENDING,
    )

    with pytest.raises(TimeConflict):
        await repos.appointments.reschedule(
            appointment_id=first.id,
            starts_at=START + timedelta(minutes=30),
            ends_at=END + timedelta(minutes=30),
            status=AppointmentStatus.CONFIRMED,
        )


@pytest.mark.asyncio
async def test_reschedule_can_overlap_own_previous_slot(repos: Repositories) -> None:
    service = await _seed_service(repos)
    created = await repos.appointments.add_appointment(
        client_user_id=CLIENT_ID,
        master_user_id=MASTER_ID,
        service_id=service.id,
        starts_at=START,
        ends_at=END,
        status=AppointmentStatus.CONFIRMED,
    )
    shifted_start = START + timedelta(minutes=30)
    shifted_end = END + timedelta(minutes=30)

    updated = await repos.appointments.reschedule(
        appointment_id=created.id,
        starts_at=shifted_start,
        ends_at=shifted_end,
        status=AppointmentStatus.CONFIRMED,
    )
    assert updated is not None
    assert updated.starts_at == shifted_start
    assert updated.ends_at == shifted_end
