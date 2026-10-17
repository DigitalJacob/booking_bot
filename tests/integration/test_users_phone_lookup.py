import pytest
from app.bot.utils.phone import normalize_phone, phone_digits
from app.domain.enums import UserRole
from app.infrastructure.database.repositories import Repositories

pytestmark = pytest.mark.integration

USER_A = 3001
USER_B = 3002
USER_C = 3003


@pytest.mark.asyncio
async def test_find_by_phone_digits_matches_normalized_forms(
    repos: Repositories,
) -> None:
    await repos.users.add_user(user_id=USER_A, language="ru", role=UserRole.CLIENT)
    await repos.users.add_user(user_id=USER_B, language="ru", role=UserRole.CLIENT)
    await repos.users.update_profile(
        user_id=USER_A,
        first_name="Ada",
        last_name="A",
        phone="+79991234567",
    )
    await repos.users.update_profile(
        user_id=USER_B,
        first_name="Bob",
        last_name="B",
        phone="8 (999) 123-45-67",
    )

    # Same digits after stripping non-digits for +7999…; 8… keeps leading 8.
    found_plus = await repos.users.find_by_phone_digits(phone_digits="79991234567")
    found_eight = await repos.users.find_by_phone_digits(phone_digits="89991234567")

    assert [user.user_id for user in found_plus] == [USER_A]
    assert [user.user_id for user in found_eight] == [USER_B]


@pytest.mark.asyncio
async def test_find_by_phone_digits_returns_all_exact_matches(
    repos: Repositories,
) -> None:
    phone = normalize_phone("+7 999 000-11-22")
    assert phone is not None
    digits = phone_digits(phone)

    for user_id, name in ((USER_A, "Ada"), (USER_C, "Cid")):
        await repos.users.add_user(
            user_id=user_id,
            language="ru",
            role=UserRole.CLIENT,
        )
        await repos.users.update_profile(
            user_id=user_id,
            first_name=name,
            last_name="X",
            phone=phone,
        )

    found = await repos.users.find_by_phone_digits(phone_digits=digits)
    assert [user.user_id for user in found] == [USER_A, USER_C]


@pytest.mark.asyncio
async def test_find_by_phone_digits_empty_or_unknown(
    repos: Repositories,
) -> None:
    await repos.users.add_user(user_id=USER_A, language="ru", role=UserRole.CLIENT)
    await repos.users.update_profile(
        user_id=USER_A,
        first_name="Ada",
        last_name="A",
        phone="+79991112233",
    )

    assert await repos.users.find_by_phone_digits(phone_digits="") == []
    assert await repos.users.find_by_phone_digits(phone_digits="abc") == []
    assert await repos.users.find_by_phone_digits(phone_digits="0000000000") == []
