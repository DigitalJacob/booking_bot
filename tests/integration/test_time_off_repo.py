from datetime import UTC, datetime, timedelta

import pytest
from app.domain.enums import UserRole
from app.infrastructure.database.repositories import Repositories

pytestmark = pytest.mark.integration

MASTER_ID = 1201
DAY = datetime(2026, 11, 10, 0, 0, tzinfo=UTC)


async def _seed_master(repos: Repositories) -> None:
    await repos.users.add_user(
        user_id=MASTER_ID,
        language="ru",
        role=UserRole.MASTER,
    )


@pytest.mark.asyncio
async def test_list_by_master_returns_overlapping_blocks_only(
        repos: Repositories,
) -> None:
    await _seed_master(repos)

    early = await repos.time_off.add(
        master_user_id=MASTER_ID,
        starts_at=DAY + timedelta(hours=8),
        ends_at=DAY + timedelta(hours=9),
        note="early",
    )
    overlapping = await repos.time_off.add(
        master_user_id=MASTER_ID,
        starts_at=DAY + timedelta(hours=9),
        ends_at=DAY + timedelta(hours=11),
        note="overlap",
    )
    late = await repos.time_off.add(
        master_user_id=MASTER_ID,
        starts_at=DAY + timedelta(hours=12),
        ends_at=DAY + timedelta(hours=13),
        note="late",
    )

    # Query window [10:00, 12:00): overlap yes; early/late no (half-open).
    found = await repos.time_off.list_by_master(
        master_user_id=MASTER_ID,
        from_dt=DAY + timedelta(hours=10),
        to_dt=DAY + timedelta(hours=12),
    )
    ids = {row.id for row in found}
    assert overlapping.id in ids
    assert early.id not in ids
    assert late.id not in ids
