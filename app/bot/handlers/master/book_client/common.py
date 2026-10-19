"""Shared helpers for master book-client lookup and FSM prompts."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Literal, TypedDict

from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, Message

from app.bot.keyboards.book_client import (
    get_book_client_cancel_kb,
    get_book_client_existing_manual_kb,
)
from app.bot.utils.contacts import client_contact
from app.bot.utils.hub_nav import HUB_MESSAGE_ID_KEY, clear_state_keep_hub, show_hub
from app.bot.utils.phone import normalize_phone, phone_digits
from app.bot.utils.telegram import is_not_modified
from app.domain.enums import UserRole
from app.domain.models import ManualClient, User
from app.infrastructure.database.repositories import Repositories

RESULT_LIMIT = 8

ClientKind = Literal["tg", "manual"]


class BookClientTargetFields(TypedDict):
    book_client_kind: ClientKind
    book_client_ref_id: int


class BookClientDraftFields(TypedDict, total=False):
    book_client_new_name: str | None
    book_client_new_phone: str | None
    book_client_new_digits: str | None
    book_client_prefill_phone: str | None
    book_client_prefill_digits: str | None


@dataclass(frozen=True, slots=True)
class PhonePrefill:
    phone: str
    digits: str


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


@dataclass(frozen=True, slots=True)
class ResolvedClientTarget:
    kind: ClientKind
    ref_id: int


@dataclass(frozen=True, slots=True)
class NewClientDraft:
    name: str
    phone: str
    digits: str


def get_book_client_target(data: Mapping[str, Any]) -> ResolvedClientTarget | None:
    kind = data.get("book_client_kind")
    ref_id = data.get("book_client_ref_id")
    if kind not in ("tg", "manual") or not isinstance(ref_id, int):
        return None
    return ResolvedClientTarget(kind=kind, ref_id=ref_id)


async def set_book_client_target(
    state: FSMContext,
    *,
    kind: ClientKind,
    ref_id: int,
    clear_draft: bool = False,
) -> None:
    target: BookClientTargetFields = {
        "book_client_kind": kind,
        "book_client_ref_id": ref_id,
    }
    if not clear_draft:
        await state.update_data(**target)
        return
    draft: BookClientDraftFields = {
        "book_client_new_name": None,
        "book_client_new_phone": None,
        "book_client_new_digits": None,
        "book_client_prefill_phone": None,
        "book_client_prefill_digits": None,
    }
    await state.update_data(**target, **draft)


def parse_phone_prefill(raw: str) -> PhonePrefill | None:
    phone = normalize_phone(raw)
    if phone is None:
        return None
    return PhonePrefill(phone=phone, digits=phone_digits(phone))


def get_phone_prefill(data: Mapping[str, Any]) -> PhonePrefill | None:
    phone = data.get("book_client_prefill_phone")
    digits = data.get("book_client_prefill_digits")
    if not isinstance(phone, str) or not phone or not isinstance(digits, str) or not digits:
        return None
    return PhonePrefill(phone=phone, digits=digits)


async def set_phone_prefill(
    state: FSMContext,
    *,
    phone: str,
    digits: str,
) -> None:
    await state.update_data(
        book_client_prefill_phone=phone,
        book_client_prefill_digits=digits,
    )


async def clear_phone_prefill(state: FSMContext) -> None:
    await state.update_data(
        book_client_prefill_phone=None,
        book_client_prefill_digits=None,
    )


def get_new_client_name(data: Mapping[str, Any]) -> str | None:
    name = data.get("book_client_new_name")
    if isinstance(name, str) and name:
        return name
    return None


def get_new_client_draft(data: Mapping[str, Any]) -> NewClientDraft | None:
    name = get_new_client_name(data)
    phone = data.get("book_client_new_phone")
    digits = data.get("book_client_new_digits")
    if (
        name is None
        or not isinstance(phone, str)
        or not phone
        or not isinstance(digits, str)
        or not digits
    ):
        return None
    return NewClientDraft(name=name, phone=phone, digits=digits)


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


async def resolve_pick_target(
    *,
    repos: Repositories,
    master_user_id: int,
    kind: str,
    ref_id: int,
) -> ResolvedClientTarget | None:
    """Validate a pick callback: eligible TG client or this master's manual."""
    if kind == "tg":
        target = await repos.users.get_user_by_id(user_id=ref_id)
        if target is None or not is_eligible_tg_client(
            user=target,
            master_user_id=master_user_id,
        ):
            return None
        return ResolvedClientTarget(kind="tg", ref_id=ref_id)
    if kind == "manual":
        manual = await repos.manual_clients.get(
            manual_client_id=ref_id,
            master_user_id=master_user_id,
        )
        if manual is None:
            return None
        return ResolvedClientTarget(kind="manual", ref_id=ref_id)
    return None


async def show_existing_manual_prompt(
    *,
    message: Message,
    state: FSMContext,
    i18n: dict[str, str],
    client: ManualClient,
) -> None:
    await show_book_client_prompt(
        message=message,
        state=state,
        text=i18n.get("book_client_existing_manual").format(
            client_name=client.name,
            client_phone=client.phone,
        ),
        i18n=i18n,
        reply_markup=get_book_client_existing_manual_kb(
            manual_client_id=client.id,
            i18n=i18n,
        ),
    )


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

    def add_tg(user: User | None) -> None:
        if user is None or not is_eligible_tg_client(
            user=user,
            master_user_id=master_user_id,
        ):
            return
        _add_hit(hits, seen, _tg_hit(user, i18n))

    def add_manual(client: ManualClient | None) -> None:
        if client is None:
            return
        _add_hit(hits, seen, _manual_hit(client, i18n))

    if query.isdigit():
        add_tg(await repos.users.get_user_by_id(user_id=int(query)))
        if len(query) >= 10:
            for user in await repos.users.find_by_phone_digits(phone_digits=query):
                add_tg(user)
            add_manual(
                await repos.manual_clients.find_by_phone(
                    master_user_id=master_user_id,
                    phone_digits=query,
                )
            )
        return hits

    if query.startswith("@"):
        add_tg(await repos.users.get_user_by_username(username=query))
        return hits

    normalized = normalize_phone(query)
    digits = phone_digits(normalized or query)
    if digits:
        for user in await repos.users.find_by_phone_digits(phone_digits=digits):
            add_tg(user)
        add_manual(
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
        add_manual(client)

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
