"""Shared helpers for master book-client lookup and FSM prompts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, Message

from app.bot.keyboards.book_client import get_book_client_cancel_kb
from app.bot.utils.format import client_contact
from app.bot.utils.hub_nav import HUB_MESSAGE_ID_KEY, clear_state_keep_hub, show_hub
from app.bot.utils.phone import normalize_phone, phone_digits
from app.bot.utils.telegram import is_not_modified
from app.domain.enums import UserRole
from app.domain.models import ManualClient, User
from app.infrastructure.database.repositories import Repositories

RESULT_LIMIT = 8

ClientKind = Literal["tg", "manual"]


@dataclass(frozen=True, slots=True)
class ClientSearchHit:
    kind: ClientKind
    ref_id: int
    title: str
    subtitle: str

    @property
    def button_label(self) -> str:
        label = f"{self.title} · {self.subtitle}"
        return label if len(label) <= 64 else f"{label[:61]}..."


def is_eligible_tg_client(*, user: User, master_user_id: int) -> bool:
    return user.role == UserRole.CLIENT and not user.banned and user.user_id != master_user_id


def _tg_hit(user: User, i18n: dict[str, str]) -> ClientSearchHit:
    name, phone = client_contact(user)
    mark = i18n.get("book_client_mark_tg")
    return ClientSearchHit(
        kind="tg",
        ref_id=user.user_id,
        title=f"{mark} {name}",
        subtitle=phone,
    )


def _manual_hit(client: ManualClient, i18n: dict[str, str]) -> ClientSearchHit:
    mark = i18n.get("book_client_mark_manual")
    return ClientSearchHit(
        kind="manual",
        ref_id=client.id,
        title=f"{mark} {client.name}",
        subtitle=client.phone,
    )


def _add_hit(
    hits: list[ClientSearchHit],
    seen: set[tuple[str, int]],
    hit: ClientSearchHit,
) -> None:
    key = (hit.kind, hit.ref_id)
    if key in seen or len(hits) >= RESULT_LIMIT:
        return
    seen.add(key)
    hits.append(hit)


async def search_book_clients(
    *,
    repos: Repositories,
    master_user_id: int,
    raw: str,
    i18n: dict[str, str],
) -> list[ClientSearchHit]:
    query = raw.strip()
    if not query:
        return []

    hits: list[ClientSearchHit] = []
    seen: set[tuple[str, int]] = set()

    async def add_tg(user: User | None) -> None:
        if user is None or not is_eligible_tg_client(
            user=user,
            master_user_id=master_user_id,
        ):
            return
        _add_hit(hits, seen, _tg_hit(user, i18n))

    async def add_manual(client: ManualClient | None) -> None:
        if client is None:
            return
        _add_hit(hits, seen, _manual_hit(client, i18n))

    if query.isdigit():
        await add_tg(await repos.users.get_user_by_id(user_id=int(query)))
        if len(query) >= 10:
            for user in await repos.users.find_by_phone_digits(phone_digits=query):
                await add_tg(user)
            await add_manual(
                await repos.manual_clients.find_by_phone(
                    master_user_id=master_user_id,
                    phone_digits=query,
                )
            )
        return hits

    if query.startswith("@"):
        await add_tg(await repos.users.get_user_by_username(username=query))
        return hits

    normalized = normalize_phone(query)
    digits = phone_digits(normalized or query)
    if digits:
        for user in await repos.users.find_by_phone_digits(phone_digits=digits):
            await add_tg(user)
        await add_manual(
            await repos.manual_clients.find_by_phone(
                master_user_id=master_user_id,
                phone_digits=digits,
            )
        )

    for client in await repos.manual_clients.search(
        master_user_id=master_user_id,
        query=query,
        limit=RESULT_LIMIT,
    ):
        await add_manual(client)

    return hits[:RESULT_LIMIT]


async def show_book_client_prompt(
    *,
    message: Message,
    state: FSMContext,
    text: str,
    i18n: dict[str, str],
    reply_markup: InlineKeyboardMarkup | None = None,
) -> None:
    """Show FSM prompt on the sticky hub message when possible."""
    data = await state.get_data()
    sticky_id = data.get(HUB_MESSAGE_ID_KEY)
    kb = reply_markup if reply_markup is not None else get_book_client_cancel_kb(i18n)

    if sticky_id is not None:
        try:
            await message.bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=int(sticky_id),
                text=text,
                reply_markup=kb,
            )
            return
        except TelegramBadRequest as exc:
            if is_not_modified(exc):
                return

    await message.answer(text=text, reply_markup=kb)


async def cancel_book_client_flow(
    *,
    message: Message,
    state: FSMContext,
    user: User,
    i18n: dict[str, str],
) -> None:
    await clear_state_keep_hub(state)
    await show_hub(
        message=message,
        user=user,
        i18n=i18n,
        state=state,
    )
