"""Sticky funnel entry, existing-manual create, and phone prefill for book-client."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import StorageKey
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message
from aiogram.types import User as TgUser
from app.bot.handlers.master.book_client.common import (
    get_phone_prefill,
    parse_phone_prefill,
    set_phone_prefill,
)
from app.bot.handlers.master.book_client.create import (
    _create_manual_and_enter,
    process_new_client_name,
)
from app.bot.handlers.master.book_client.funnel import start_slot_funnel
from app.bot.keyboards.book_client import BookClientPickCallback
from app.bot.states.states import MasterBookSG
from app.bot.utils.hub_nav import HUB_MESSAGE_ID_KEY
from app.domain.enums import UserRole
from app.domain.models import User

from tests.factories import (
    MASTER_ID,
    NOW,
    make_manual_client,
    make_repos,
    make_service,
)

I18N = {
    "book_choose_service": "Choose a service",
    "book_no_services": "No services",
    "book_client_ask_phone": "Enter phone",
    "book_client_ask_name": "Enter name",
    "book_client_invalid_name": "Invalid name",
    "book_client_existing_manual": "{client_name} · {client_phone} already exists",
    "book_client_use_existing_button": "Use existing",
    "book_client_cancel_button": "Cancel",
    "service_button": "{title} ({duration} min)",
    "book_back_button": "Back",
    "book_cancel_button": "Cancel",
}

STICKY_ID = 42
USER_MSG_ID = 9001


def _master() -> User:
    return User(
        id=MASTER_ID,
        user_id=MASTER_ID,
        username="master",
        language="ru",
        role=UserRole.MASTER,
        banned=False,
        first_name="Master",
        last_name=None,
        phone=None,
        pdn_consent_at=None,
        pdn_consent_version=None,
        created_at=NOW,
    )


def _fsm() -> FSMContext:
    return FSMContext(
        storage=MemoryStorage(),
        key=StorageKey(bot_id=1, chat_id=1, user_id=MASTER_ID),
    )


async def _prepare_state(state: FSMContext, *, sticky_id: int = STICKY_ID) -> None:
    await state.update_data({HUB_MESSAGE_ID_KEY: sticky_id})


def _user_text_message() -> MagicMock:
    """Inbound phone/name text: not a bot message, cannot be edited."""
    message = MagicMock(spec=Message)
    message.message_id = USER_MSG_ID
    message.chat = MagicMock()
    message.chat.id = 1
    message.from_user = MagicMock(spec=TgUser)
    message.from_user.is_bot = False
    message.bot = AsyncMock()
    message.bot.edit_message_text = AsyncMock()
    message.bot.edit_message_reply_markup = AsyncMock()
    message.edit_text = AsyncMock()
    message.answer = AsyncMock()
    message.delete = AsyncMock()
    return message


@pytest.mark.asyncio
async def test_start_slot_funnel_edits_sticky_not_user_message():
    repos = make_repos(services=[make_service()])
    state = _fsm()
    await _prepare_state(state)
    message = _user_text_message()

    started = await start_slot_funnel(
        message=message,
        state=state,
        repos=repos,
        master_user_id=MASTER_ID,
        i18n=I18N,
    )

    assert started is True
    assert await state.get_state() == MasterBookSG.choosing_service.state
    message.bot.edit_message_text.assert_awaited()
    call_kwargs = message.bot.edit_message_text.await_args.kwargs
    assert call_kwargs["message_id"] == STICKY_ID
    assert call_kwargs["text"] == I18N["book_choose_service"]
    message.edit_text.assert_not_awaited()
    message.answer.assert_not_awaited()


@pytest.mark.asyncio
async def test_create_existing_manual_offers_without_second_create():
    existing = make_manual_client(name="Ivan", phone="+79990001122", phone_digits="79990001122")
    repos = make_repos(manual_clients=[existing])
    create_spy = AsyncMock(wraps=repos.manual_clients.create)
    repos.manual_clients.create = create_spy

    state = _fsm()
    await _prepare_state(state)
    message = _user_text_message()

    await _create_manual_and_enter(
        message=message,
        state=state,
        repos=repos,
        user=_master(),
        i18n=I18N,
        name="Ivan",
        phone=existing.phone,
        digits=existing.phone_digits,
    )

    create_spy.assert_not_awaited()
    message.bot.edit_message_text.assert_awaited()
    call_kwargs = message.bot.edit_message_text.await_args.kwargs
    assert call_kwargs["message_id"] == STICKY_ID
    assert "Ivan" in call_kwargs["text"]
    assert existing.phone in call_kwargs["text"]

    markup = call_kwargs["reply_markup"]
    packed = markup.inline_keyboard[0][0].callback_data
    assert packed == BookClientPickCallback(kind="manual", ref_id=existing.id).pack()
    assert await state.get_state() != MasterBookSG.choosing_service.state


def test_parse_phone_prefill_accepts_phone_rejects_username():
    ok = parse_phone_prefill("+7 999 123-45-67")
    assert ok is not None
    assert ok.phone == "+79991234567"
    assert ok.digits == "79991234567"
    assert parse_phone_prefill("@ada_client") is None
    assert parse_phone_prefill("ada") is None


@pytest.mark.asyncio
async def test_new_client_name_with_prefill_skips_phone_prompt_and_creates():
    repos = make_repos(services=[make_service()])
    repos.users = MagicMock()
    repos.users.find_by_phone_digits = AsyncMock(return_value=[])
    create_spy = AsyncMock(wraps=repos.manual_clients.create)
    repos.manual_clients.create = create_spy

    state = _fsm()
    await _prepare_state(state)
    await set_phone_prefill(
        state,
        phone="+79990001122",
        digits="79990001122",
    )
    message = _user_text_message()
    message.text = "Ivan"

    await process_new_client_name(
        message,
        state,
        repos,
        _master(),
        I18N,
    )

    create_spy.assert_awaited_once()
    assert create_spy.await_args.kwargs["phone"] == "+79990001122"
    assert create_spy.await_args.kwargs["phone_digits"] == "79990001122"
    assert create_spy.await_args.kwargs["name"] == "Ivan"
    assert get_phone_prefill(await state.get_data()) is None
    ask_phone_calls = [
        call
        for call in message.bot.edit_message_text.await_args_list
        if call.kwargs.get("text") == I18N["book_client_ask_phone"]
    ]
    assert ask_phone_calls == []
    assert await state.get_state() == MasterBookSG.choosing_service.state


@pytest.mark.asyncio
async def test_new_client_name_without_prefill_asks_phone():
    repos = make_repos()
    state = _fsm()
    await _prepare_state(state)
    message = _user_text_message()
    message.text = "Ivan"

    await process_new_client_name(
        message,
        state,
        repos,
        _master(),
        I18N,
    )

    assert await state.get_state() == MasterBookSG.new_phone.state
    message.bot.edit_message_text.assert_awaited()
    assert message.bot.edit_message_text.await_args.kwargs["text"] == I18N["book_client_ask_phone"]
