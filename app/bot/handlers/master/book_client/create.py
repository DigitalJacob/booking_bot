"""Create a manual client (name → phone) before the slot funnel."""

from __future__ import annotations

from aiogram import F
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.bot.handlers.master.book_client.common import (
    ClientKind,
    cancel_book_client_flow,
    get_new_client_draft,
    get_new_client_name,
    is_eligible_tg_client,
    resolve_pick_target,
    set_book_client_target,
    show_book_client_prompt,
    show_existing_manual_prompt,
)
from app.bot.handlers.master.book_client.funnel import start_slot_funnel
from app.bot.handlers.master.book_client.router import book_client_router
from app.bot.keyboards.book_client import (
    BookClientNavCallback,
    BookClientPickCallback,
    get_book_client_tg_offer_kb,
)
from app.bot.states.states import MasterBookSG
from app.bot.utils.contacts import client_contact
from app.bot.utils.phone import normalize_phone, phone_digits
from app.bot.utils.telegram import delete_user_input
from app.domain.exceptions import ManualClientPhoneTaken
from app.domain.models import User
from app.infrastructure.database.repositories import Repositories

_NAME_MIN = 2
_NAME_MAX = 100


async def start_new_client_flow(
    *,
    message: Message,
    state: FSMContext,
    i18n: dict[str, str],
) -> None:
    await state.set_state(MasterBookSG.new_name)
    await show_book_client_prompt(
        message=message,
        state=state,
        text=i18n.get("book_client_ask_name"),
        i18n=i18n,
    )


async def _enter_funnel(
    *,
    message: Message,
    state: FSMContext,
    repos: Repositories,
    user: User,
    i18n: dict[str, str],
    kind: ClientKind,
    ref_id: int,
) -> None:
    await set_book_client_target(
        state,
        kind=kind,
        ref_id=ref_id,
        clear_draft=True,
    )
    started = await start_slot_funnel(
        message=message,
        state=state,
        repos=repos,
        master_user_id=user.user_id,
        i18n=i18n,
    )
    if not started:
        await cancel_book_client_flow(
            message=message,
            state=state,
            user=user,
            i18n=i18n,
        )


async def _create_manual_and_enter(
    *,
    message: Message,
    state: FSMContext,
    repos: Repositories,
    user: User,
    i18n: dict[str, str],
    name: str,
    phone: str,
    digits: str,
) -> None:
    existing = await repos.manual_clients.find_by_phone(
        master_user_id=user.user_id,
        phone_digits=digits,
    )
    if existing is not None:
        await show_existing_manual_prompt(
            message=message,
            state=state,
            i18n=i18n,
            client=existing,
        )
        return

    try:
        created = await repos.manual_clients.create(
            master_user_id=user.user_id,
            name=name,
            phone=phone,
            phone_digits=digits,
        )
    except ManualClientPhoneTaken:
        existing = await repos.manual_clients.find_by_phone(
            master_user_id=user.user_id,
            phone_digits=digits,
        )
        if existing is None:
            await show_book_client_prompt(
                message=message,
                state=state,
                text=i18n.get("book_client_ask_phone"),
                i18n=i18n,
            )
            return
        await show_existing_manual_prompt(
            message=message,
            state=state,
            i18n=i18n,
            client=existing,
        )
        return

    await _enter_funnel(
        message=message,
        state=state,
        repos=repos,
        user=user,
        i18n=i18n,
        kind="manual",
        ref_id=created.id,
    )


@book_client_router.message(StateFilter(MasterBookSG.new_name), F.text)
async def process_new_client_name(
    message: Message,
    state: FSMContext,
    i18n: dict[str, str],
) -> None:
    name = (message.text or "").strip()
    await delete_user_input(message)
    if len(name) < _NAME_MIN or len(name) > _NAME_MAX:
        await show_book_client_prompt(
            message=message,
            state=state,
            text=i18n.get("book_client_invalid_name"),
            i18n=i18n,
        )
        return

    await state.update_data(book_client_new_name=name)
    await state.set_state(MasterBookSG.new_phone)
    await show_book_client_prompt(
        message=message,
        state=state,
        text=i18n.get("book_client_ask_phone"),
        i18n=i18n,
    )


@book_client_router.message(StateFilter(MasterBookSG.new_phone), F.text)
async def process_new_client_phone(
    message: Message,
    state: FSMContext,
    repos: Repositories,
    user: User,
    i18n: dict[str, str],
) -> None:
    raw = (message.text or "").strip()
    await delete_user_input(message)

    phone = normalize_phone(raw)
    if phone is None:
        await show_book_client_prompt(
            message=message,
            state=state,
            text=i18n.get("book_client_invalid_phone"),
            i18n=i18n,
        )
        return

    digits = phone_digits(phone)
    data = await state.get_data()
    name = get_new_client_name(data)
    if name is None:
        await state.set_state(MasterBookSG.new_name)
        await show_book_client_prompt(
            message=message,
            state=state,
            text=i18n.get("book_client_ask_name"),
            i18n=i18n,
        )
        return

    await state.update_data(
        book_client_new_phone=phone,
        book_client_new_digits=digits,
    )

    existing = await repos.manual_clients.find_by_phone(
        master_user_id=user.user_id,
        phone_digits=digits,
    )
    if existing is not None:
        await show_existing_manual_prompt(
            message=message,
            state=state,
            i18n=i18n,
            client=existing,
        )
        return

    for candidate in await repos.users.find_by_phone_digits(phone_digits=digits):
        if is_eligible_tg_client(user=candidate, master_user_id=user.user_id):
            tg_name, tg_phone = client_contact(candidate)
            await show_book_client_prompt(
                message=message,
                state=state,
                text=i18n.get("book_client_tg_offer").format(
                    client_name=tg_name,
                    client_phone=tg_phone,
                ),
                i18n=i18n,
                reply_markup=get_book_client_tg_offer_kb(
                    user_id=candidate.user_id,
                    i18n=i18n,
                ),
            )
            return

    await _create_manual_and_enter(
        message=message,
        state=state,
        repos=repos,
        user=user,
        i18n=i18n,
        name=name,
        phone=phone,
        digits=digits,
    )


@book_client_router.callback_query(
    BookClientPickCallback.filter(),
    StateFilter(MasterBookSG.new_phone),
)
async def process_new_client_pick(
    callback: CallbackQuery,
    callback_data: BookClientPickCallback,
    state: FSMContext,
    repos: Repositories,
    user: User,
    i18n: dict[str, str],
) -> None:
    target = await resolve_pick_target(
        repos=repos,
        master_user_id=user.user_id,
        kind=callback_data.kind,
        ref_id=callback_data.ref_id,
    )
    if target is None:
        await callback.answer(
            text=i18n.get("book_client_target_lost"),
            show_alert=True,
        )
        return

    await callback.answer()
    await _enter_funnel(
        message=callback.message,
        state=state,
        repos=repos,
        user=user,
        i18n=i18n,
        kind=target.kind,
        ref_id=target.ref_id,
    )


@book_client_router.callback_query(
    BookClientNavCallback.filter(F.action == "create_manual"),
    StateFilter(MasterBookSG.new_phone),
)
async def process_create_manual_anyway(
    callback: CallbackQuery,
    state: FSMContext,
    repos: Repositories,
    user: User,
    i18n: dict[str, str],
) -> None:
    draft = get_new_client_draft(await state.get_data())
    if draft is None:
        await callback.answer(
            text=i18n.get("book_client_target_lost"),
            show_alert=True,
        )
        await state.set_state(MasterBookSG.new_name)
        await show_book_client_prompt(
            message=callback.message,
            state=state,
            text=i18n.get("book_client_ask_name"),
            i18n=i18n,
        )
        return

    await callback.answer()
    await _create_manual_and_enter(
        message=callback.message,
        state=state,
        repos=repos,
        user=user,
        i18n=i18n,
        name=draft.name,
        phone=draft.phone,
        digits=draft.digits,
    )
