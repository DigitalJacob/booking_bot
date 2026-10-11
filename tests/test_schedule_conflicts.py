from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

from app.domain.enums import AppointmentStatus
from app.domain.services.schedule_conflicts import ScheduleConflictsService

from tests.factories import MASTER_ID, make_appointment, make_repos

_TZ = "Europe/Moscow"
_ZONE = ZoneInfo(_TZ)


def _local(day: date, hour: int, minute: int = 0) -> datetime:
    return datetime(day.year, day.month, day.day, hour, minute, tzinfo=_ZONE)


async def test_active_overlapping_finds_partial_overlap():
    day = date(2026, 10, 11)
    appointment = make_appointment(
        starts_at=_local(day, 10),
        ends_at=_local(day, 11),
    )
    service = ScheduleConflictsService(make_repos(appointments=[appointment]))

    found = await service.active_overlapping(
        master_user_id=MASTER_ID,
        starts_at=_local(day, 10, 30),
        ends_at=_local(day, 12),
    )

    assert [item.id for item in found] == [appointment.id]


async def test_active_overlapping_includes_slot_that_started_before_block():
    """Widen left so a long slot that began yesterday still matches."""
    day = date(2026, 10, 11)
    appointment = make_appointment(
        starts_at=_local(day, 9) - timedelta(hours=2),
        ends_at=_local(day, 10, 30),
    )
    service = ScheduleConflictsService(make_repos(appointments=[appointment]))

    found = await service.active_overlapping(
        master_user_id=MASTER_ID,
        starts_at=_local(day, 10),
        ends_at=_local(day, 11),
    )

    assert [item.id for item in found] == [appointment.id]


async def test_active_overlapping_ignores_adjacent_half_open():
    day = date(2026, 10, 11)
    appointment = make_appointment(
        starts_at=_local(day, 9),
        ends_at=_local(day, 10),
    )
    service = ScheduleConflictsService(make_repos(appointments=[appointment]))

    found = await service.active_overlapping(
        master_user_id=MASTER_ID,
        starts_at=_local(day, 10),
        ends_at=_local(day, 11),
    )

    assert found == []


async def test_active_overlapping_skips_cancelled():
    day = date(2026, 10, 11)
    appointment = make_appointment(
        starts_at=_local(day, 10),
        ends_at=_local(day, 11),
        status=AppointmentStatus.CANCELLED,
    )
    service = ScheduleConflictsService(make_repos(appointments=[appointment]))

    found = await service.active_overlapping(
        master_user_id=MASTER_ID,
        starts_at=_local(day, 10),
        ends_at=_local(day, 11),
    )

    assert found == []


async def test_active_on_local_days_empty_returns_empty():
    service = ScheduleConflictsService(
        make_repos(appointments=[make_appointment()]),
    )

    found = await service.active_on_local_days(
        master_user_id=MASTER_ID,
        days=set(),
        timezone=_TZ,
    )

    assert found == []


async def test_active_on_local_days_filters_by_local_date():
    day = date(2026, 10, 11)
    other = date(2026, 10, 12)
    on_day = make_appointment(
        appointment_id=1,
        starts_at=_local(day, 15),
        ends_at=_local(day, 16),
    )
    next_day = make_appointment(
        appointment_id=2,
        starts_at=_local(other, 10),
        ends_at=_local(other, 11),
    )
    # UTC midnight can be previous local evening in Moscow (+3).
    utc_edge = make_appointment(
        appointment_id=3,
        starts_at=datetime(2026, 10, 10, 22, 0, tzinfo=UTC),
        ends_at=datetime(2026, 10, 10, 23, 0, tzinfo=UTC),
    )
    service = ScheduleConflictsService(
        make_repos(appointments=[on_day, next_day, utc_edge]),
    )

    found = await service.active_on_local_days(
        master_user_id=MASTER_ID,
        days={day},
        timezone=_TZ,
    )

    assert sorted(item.id for item in found) == [1, 3]


async def test_active_on_local_days_skips_cancelled():
    day = date(2026, 10, 11)
    appointment = make_appointment(
        starts_at=_local(day, 12),
        ends_at=_local(day, 13),
        status=AppointmentStatus.CANCELLED,
    )
    service = ScheduleConflictsService(make_repos(appointments=[appointment]))

    found = await service.active_on_local_days(
        master_user_id=MASTER_ID,
        days={day},
        timezone=_TZ,
    )

    assert found == []
