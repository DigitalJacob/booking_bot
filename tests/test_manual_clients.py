"""Unit tests for FakeManualClientsRepository create uniqueness."""

import pytest
from app.domain.exceptions import ManualClientPhoneTaken

from tests.factories import (
    MASTER_ID,
    FakeManualClientsRepository,
    make_manual_client,
)


@pytest.mark.asyncio
async def test_create_duplicate_phone_raises_domain_error() -> None:
    existing = make_manual_client(
        manual_client_id=1,
        master_user_id=MASTER_ID,
        phone="+79991234567",
        phone_digits="79991234567",
    )
    repo = FakeManualClientsRepository([existing])

    with pytest.raises(ManualClientPhoneTaken):
        await repo.create(
            master_user_id=MASTER_ID,
            name="Other",
            phone="+7 999 123-45-67",
            phone_digits="79991234567",
        )

    found = await repo.find_by_phone(
        master_user_id=MASTER_ID,
        phone_digits="79991234567",
    )
    assert found is not None
    assert found.id == existing.id
