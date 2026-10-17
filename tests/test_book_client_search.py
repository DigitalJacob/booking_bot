from dataclasses import dataclass

import pytest
from app.bot.handlers.master.book_client.common import search_book_clients
from app.domain.enums import UserRole
from app.domain.models import User

from tests.factories import (
    CLIENT_ID,
    MASTER_ID,
    NOW,
    OTHER_ID,
    FakeManualClientsRepository,
    make_manual_client,
)

I18N = {
    "book_client_mark_tg": "In bot",
    "book_client_mark_manual": "No bot",
}


def _user(
    *,
    user_id: int,
    role: UserRole = UserRole.CLIENT,
    banned: bool = False,
    username: str | None = None,
    first_name: str = "Ada",
    phone: str | None = "+79991234567",
) -> User:
    return User(
        id=user_id,
        user_id=user_id,
        username=username,
        language="ru",
        role=role,
        banned=banned,
        first_name=first_name,
        last_name="Client",
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

    async def get_user_by_username(self, *, username: str) -> User | None:
        needle = username.lstrip("@").lower()
        for user in self._users.values():
            if user.username and user.username.lower() == needle:
                return user
        return None

    async def find_by_phone_digits(self, *, phone_digits: str) -> list[User]:
        digits = "".join(ch for ch in phone_digits if ch.isdigit())
        return [
            user
            for user in self._users.values()
            if user.phone and "".join(ch for ch in user.phone if ch.isdigit()) == digits
        ]


@dataclass
class _Repos:
    users: _FakeUsersRepository
    manual_clients: FakeManualClientsRepository


@pytest.mark.asyncio
async def test_search_by_telegram_id():
    repos = _Repos(
        users=_FakeUsersRepository([_user(user_id=CLIENT_ID)]),
        manual_clients=FakeManualClientsRepository(),
    )
    hits = await search_book_clients(
        repos=repos,
        master_user_id=MASTER_ID,
        raw=str(CLIENT_ID),
        i18n=I18N,
    )
    assert len(hits) == 1
    assert hits[0].kind == "tg"
    assert hits[0].ref_id == CLIENT_ID


@pytest.mark.asyncio
async def test_search_skips_banned_master_and_non_clients():
    repos = _Repos(
        users=_FakeUsersRepository(
            [
                _user(user_id=CLIENT_ID, banned=True),
                _user(user_id=OTHER_ID, role=UserRole.MASTER),
                _user(user_id=MASTER_ID),
            ]
        ),
        manual_clients=FakeManualClientsRepository(),
    )
    for raw in (str(CLIENT_ID), str(OTHER_ID), str(MASTER_ID)):
        hits = await search_book_clients(
            repos=repos,
            master_user_id=MASTER_ID,
            raw=raw,
            i18n=I18N,
        )
        assert hits == []


@pytest.mark.asyncio
async def test_search_by_username_and_phone_and_manual_name():
    manual = make_manual_client(name="Ivan Walkin", phone="+79990001122")
    repos = _Repos(
        users=_FakeUsersRepository(
            [
                _user(user_id=CLIENT_ID, username="ada_client", phone="+79991234567"),
            ]
        ),
        manual_clients=FakeManualClientsRepository([manual]),
    )

    by_username = await search_book_clients(
        repos=repos,
        master_user_id=MASTER_ID,
        raw="@ada_client",
        i18n=I18N,
    )
    by_phone = await search_book_clients(
        repos=repos,
        master_user_id=MASTER_ID,
        raw="+7 999 123-45-67",
        i18n=I18N,
    )
    by_name = await search_book_clients(
        repos=repos,
        master_user_id=MASTER_ID,
        raw="ivan",
        i18n=I18N,
    )

    assert [hit.ref_id for hit in by_username] == [CLIENT_ID]
    assert by_phone[0].kind == "tg"
    assert by_phone[0].ref_id == CLIENT_ID
    assert by_name[0].kind == "manual"
    assert by_name[0].ref_id == manual.id
