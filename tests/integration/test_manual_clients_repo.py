import pytest
from app.bot.utils.phone import normalize_phone, phone_digits
from app.domain.enums import UserRole
from app.domain.exceptions import ManualClientPhoneTaken
from app.infrastructure.database.repositories import Repositories

pytestmark = pytest.mark.integration

MASTER_A = 1301
MASTER_B = 1302


async def _seed_masters(repos: Repositories) -> None:
    for user_id in (MASTER_A, MASTER_B):
        await repos.users.add_user(
            user_id=user_id,
            language="ru",
            role=UserRole.MASTER,
        )


@pytest.mark.asyncio
async def test_create_get_and_find_by_phone(repos: Repositories) -> None:
    await _seed_masters(repos)
    raw = "+7 999 111-22-33"
    phone = normalize_phone(raw)
    assert phone is not None
    digits = phone_digits(phone)

    created = await repos.manual_clients.create(
        master_user_id=MASTER_A,
        name="Anna",
        phone=phone,
        phone_digits=digits,
    )
    loaded = await repos.manual_clients.get(
        manual_client_id=created.id,
        master_user_id=MASTER_A,
    )
    found = await repos.manual_clients.find_by_phone(
        master_user_id=MASTER_A,
        phone_digits=digits,
    )

    assert loaded is not None
    assert loaded.id == created.id
    assert loaded.name == "Anna"
    assert found is not None
    assert found.id == created.id


@pytest.mark.asyncio
async def test_get_scoped_to_master(repos: Repositories) -> None:
    await _seed_masters(repos)
    created = await repos.manual_clients.create(
        master_user_id=MASTER_A,
        name="Anna",
        phone="+79991112233",
        phone_digits="79991112233",
    )
    assert (
        await repos.manual_clients.get(
            manual_client_id=created.id,
            master_user_id=MASTER_B,
        )
        is None
    )


@pytest.mark.asyncio
async def test_create_duplicate_phone_same_master_raises(
    repos: Repositories,
) -> None:
    await _seed_masters(repos)
    await repos.manual_clients.create(
        master_user_id=MASTER_A,
        name="Anna",
        phone="+79991112233",
        phone_digits="79991112233",
    )
    with pytest.raises(ManualClientPhoneTaken):
        await repos.manual_clients.create(
            master_user_id=MASTER_A,
            name="Anna 2",
            phone="89991112233",
            phone_digits="79991112233",
        )


@pytest.mark.asyncio
async def test_search_by_name_and_phone_digits(repos: Repositories) -> None:
    await _seed_masters(repos)
    await repos.manual_clients.create(
        master_user_id=MASTER_A,
        name="Ivan Petrov",
        phone="+79990001122",
        phone_digits="79990001122",
    )
    await repos.manual_clients.create(
        master_user_id=MASTER_A,
        name="Maria",
        phone="+79993334455",
        phone_digits="79993334455",
    )
    await repos.manual_clients.create(
        master_user_id=MASTER_B,
        name="Ivan Other Master",
        phone="+79990001122",
        phone_digits="79990001122",
    )

    by_name = await repos.manual_clients.search(
        master_user_id=MASTER_A,
        query="ivan",
    )
    by_phone = await repos.manual_clients.search(
        master_user_id=MASTER_A,
        query="9000",
    )

    assert [row.name for row in by_name] == ["Ivan Petrov"]
    assert [row.name for row in by_phone] == ["Ivan Petrov"]
