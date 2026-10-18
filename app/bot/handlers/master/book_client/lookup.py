"""Hub entry and client lookup FSM for master booking."""

from __future__ import annotations

from aiogram import F
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.bot.handlers.master.book_client.common import (
    cancel_book_client_flow,
    resolve_pick_target,
    search_book_clients,
    show_book_client_prompt,
)
from app.bot.handlers.master.book_client.create import start_new_client_flow
from app.bot.handlers.master.book_client.funnel import start_slot_funnel
from app.bot.handlers.master.book_client.router import book_client_router
from app.bot.keyboards.book_client import (
    BookClientNavCallback,
    BookClientPickCallback,
    get_book_client_results_kb,
)
from app.bot.states.states import MasterBookSG
from app.bot.utils.hub_nav import clear_state_keep_hub
from app.bot.utils.hub_registry import register
from app.bot.utils.telegram import delete_user_input
from app.domain.enums import UserRole
from app.domain.models import User
from app.infrastructure.database.repositories import Repositories


async def start_book_client_flow(
    *,
    message: Message,
    state: FSMContext,
    i18n: dict[str, str],
) -> None:
    await clear_state_keep_hub(state)
    await state.set_state(MasterBookSG.query)
    await show_book_client_prompt(
        message=message,
        state=state,
        text=i18n.get("book_client_ask_query"),
        i18n=i18n,
    )


@book_client_router.callback_query(
    BookClientNavCallback.filter(F.action == "cancel"),
    StateFilter(MasterBookSG),
)
async def process_book_client_cancel(
    callback: CallbackQuery,
    state: FSMContext,
    user: User,
    i18n: dict[str, str],
) -> None:
    await callback.answer()
    await cancel_book_client_flow(
        message=callback.message,
        state=state,
        user=user,
        i18n=i18n,
    )


@book_client_router.message(StateFilter(MasterBookSG.query))
async def process_book_client_query(
    message: Message,
    state: FSMContext,
    repos: Repositories,
    user: User,
    i18n: dict[str, str],
) -> None:
    raw = (message.text or "").strip()
    await delete_user_input(message)

    if not raw:
        await show_book_client_prompt(
            message=message,
            state=state,
            text=i18n.get("book_client_ask_query"),
            i18n=i18n,
        )
        return

    hits = await search_book_clients(
        repos=repos,
        master_user_id=user.user_id,
        raw=raw,
        i18n=i18n,
    )
    await state.set_state(MasterBookSG.picking)
    if not hits:
        text = i18n.get("book_client_empty").format(query=raw)
    else:
        text = i18n.get("book_client_results_header").format(query=raw)
    await show_book_client_prompt(
        message=message,
        state=state,
        text=text,
        i18n=i18n,
        reply_markup=get_book_client_results_kb(
            hits=[(hit.kind, hit.ref_id, hit.button_label) for hit in hits],
            i18n=i18n,
        ),
    )


@book_client_router.callback_query(
    BookClientPickCallback.filter(),
    StateFilter(MasterBookSG.picking),
)
async def process_book_client_pick(
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

    await state.update_data(
        book_client_kind=target.kind,
        book_client_ref_id=target.ref_id,
    )
    started = await start_slot_funnel(
        message=callback.message,
        state=state,
        repos=repos,
        master_user_id=user.user_id,
        i18n=i18n,
    )
    await callback.answer()
    if not started:
        await cancel_book_client_flow(
            message=callback.message,
            state=state,
            user=user,
            i18n=i18n,
        )


@book_client_router.callback_query(
    BookClientNavCallback.filter(F.action == "new"),
    StateFilter(MasterBookSG.picking, MasterBookSG.query),
)
async def process_book_client_new(
    callback: CallbackQuery,
    state: FSMContext,
    i18n: dict[str, str],
) -> None:
    await callback.answer()
    await start_new_client_flow(
        message=callback.message,
        state=state,
        i18n=i18n,
    )


async def _hub_book_client(
    *,
    message: Message,
    user: User,
    i18n: dict[str, str],
    state: FSMContext,
    **_,
) -> None:
    if user.role != UserRole.MASTER:
        return
    await state.update_data(
        hub_screen="book_client",
        hub_back="root",
    )
    await start_book_client_flow(
        message=message,
        state=state,
        i18n=i18n,
    )


register("book_client", _hub_book_client)
