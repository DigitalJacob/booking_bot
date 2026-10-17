from dataclasses import dataclass

import pytest
from app.bot.utils.format import appointment_client_contact
from app.domain.enums import UserRole
from app.domain.models import User

from tests.factories import (
    CLIENT_ID,
    NOW,
    FakeManualClientsRepository,
    make_appointment,
    make_manual_client,
)


def _make_user(
    *,
    user_id: int = CLIENT_ID,
    first_name: str = "Ada",
    last_name: str = "Lovelace",
    phone: str = "+79991112233",
) -> User:
    return User(
        id=1,
        user_id=user_id,
        username=None,
        language="ru",
        role=UserRole.CLIENT,
        banned=False,
        first_name=first_name,
        last_name=last_name,
        phone=phone,
        pdn_consent_at=None,
        pdn_consent_version=None,
        created_at=NOW,
    )


class _FakeUsersRepository:
    def __init__(self, users: list[User]) -> None:
        self._users = {user.user_id: user for user in users}

    async def get_user_by_id(self, *, user_id: int) -> User | None:
        return self._users.get(user_id)


@dataclass
class _Repos:
    users: _FakeUsersRepository
    manual_clients: FakeManualClientsRepository


@pytest.mark.asyncio
async def test_appointment_client_contact_from_telegram_user():
    repos = _Repos(
        users=_FakeUsersRepository([_make_user()]),
        manual_clients=FakeManualClientsRepository(),
    )
    appointment = make_appointment(client_user_id=CLIENT_ID)

    name, phone = await appointment_client_contact(repos, appointment)

    assert name == "Ada Lovelace"
    assert phone == "+79991112233"


@pytest.mark.asyncio
async def test_appointment_client_contact_from_manual_client():
    manual = make_manual_client(name="Ivan", phone="+79990001122")
    repos = _Repos(
        users=_FakeUsersRepository([]),
        manual_clients=FakeManualClientsRepository([manual]),
    )
    appointment = make_appointment(
        client_user_id=None,
        manual_client_id=manual.id,
    )

    name, phone = await appointment_client_contact(repos, appointment)

    assert name == "Ivan"
    assert phone == "+79990001122"


@pytest.mark.asyncio
async def test_appointment_client_contact_missing_falls_back():
    repos = _Repos(
        users=_FakeUsersRepository([]),
        manual_clients=FakeManualClientsRepository(),
    )
    appointment = make_appointment(
        client_user_id=None,
        manual_client_id=42,
    )

    name, phone = await appointment_client_contact(repos, appointment)

    assert name == "?"
    assert phone == "-"
