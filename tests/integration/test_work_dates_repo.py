from datetime import date, time

import pytest
from app.domain.enums import UserRole
from app.infrastructure.database.repositories import Repositories

pytestmark = pytest.mark.integration

MASTER_ID = 1101


async def _seed_master(repos: Repositories) -> None:
    await repos.users.add_user(
        user_id=MASTER_ID,
        language="ru",
        role=UserRole.MASTER,
    )


@pytest.mark.asyncio
async def test_upsert_updates_hours_on_unique_conflict(
        repos: Repositories,
) -> None:
    await _seed_master(repos)
    day = date(2026, 11, 3)

    first = await repos.work_dates.upsert_dates(
        master_user_id=MASTER_ID,
        work_dates=[day],
        starts_time=time(9, 0),
        ends_time=time(12, 0),
    )
    assert len(first) == 1
    assert first[0].starts_time == time(9, 0)
    assert first[0].ends_time == time(12, 0)

    second = await repos.work_dates.upsert_dates(
        master_user_id=MASTER_ID,
        work_dates=[day],
        starts_time=time(10, 0),
        ends_time=time(18, 0),
    )
    assert len(second) == 1
    assert second[0].id == first[0].id
    assert second[0].starts_time == time(10, 0)
    assert second[0].ends_time == time(18, 0)

    listed = await repos.work_dates.list_by_master(master_user_id=MASTER_ID)
    assert len(listed) == 1
    assert listed[0].starts_time == time(10, 0)


@pytest.mark.asyncio
async def test_list_by_master_half_open_date_range(repos: Repositories) -> None:
    await _seed_master(repos)
    await repos.work_dates.upsert_dates(
        master_user_id=MASTER_ID,
        work_dates=[
            date(2026, 11, 1),
            date(2026, 11, 2),
            date(2026, 11, 3),
        ],
        starts_time=time(9, 0),
        ends_time=time(12, 0),
    )

    window = await repos.work_dates.list_by_master(
        master_user_id=MASTER_ID,
        from_date=date(2026, 11, 2),
        to_date=date(2026, 11, 3),
    )
    assert [row.work_date for row in window] == [date(2026, 11, 2)]
