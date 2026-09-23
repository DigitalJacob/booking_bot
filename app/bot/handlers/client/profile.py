import re

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.bot.keyboards.hub import get_hub_back_home_kb
from app.bot.keyboards.profile import (
    ProfileNavCallback,
    get_phone_kb,
    get_profile_cancel_kb,
    remove_kb,
)
from app.bot.states.states import ProfileSG
from app.bot.utils.hub_nav import HUB_MESSAGE_ID_KEY, clear_state_keep_hub, show_hub
from app.bot.utils.hub_registry import register
from app.domain.enums import UserRole
from app.domain.models import User
from app.infrastructure.database.repositories import Repositories


profile_router = Router(name="client_profile")

_PHONE_RE = re.compile(r"^\+?\d{10,15}$")
_PROFILE_PROMPT_ID_KEY = "profile_prompt_message_id"
_PROFILE_AUX_ID_KEY = "profile_aux_message_id"


def format_profile_card(user: User, i18n: dict[str, str]) -> str:
    return i18n.get("profile_card").format(
        first_name=user.first_name or "-",
        last_name=user.last_name or "-",
        phone=user.phone or "-",
    )


def _is_not_modified(exc: TelegramBadRequest) -> bool:
    return "message is not modified" in str(exc).lower()


async def _delete_chat_message(
        *,
        message: Message,
        message_id: int | None,
) -> None:
    if message_id is None:
        return
    try:
        await message.bot.delete_message(
            chat_id=message.chat.id,
            message_id=message_id,
        )
    except TelegramBadRequest:
        pass


async def _delete_user_input(message: Message) -> None:
    """Delete the client's chat message after its content was read."""
    await _delete_chat_message(message=message, message_id=message.message_id)


async def _drop_reply_keyboard(message: Message) -> None:
    """Remove reply keyboard without leaving a visible notice in chat."""
    stub = await message.answer(text=".", reply_markup=remove_kb())
    try:
        await stub.delete()
    except TelegramBadRequest:
        pass


async def _cleanup_profile_messages(
        *,
        message: Message,
        state: FSMContext,
        drop_reply_kb: bool,
) -> None:
    data = await state.get_data()
    sticky_id = data.get(HUB_MESSAGE_ID_KEY)
    prompt_id = data.get(_PROFILE_PROMPT_ID_KEY)
    aux_id = data.get(_PROFILE_AUX_ID_KEY)

    await _delete_chat_message(message=message, message_id=aux_id)
    if prompt_id is not None and prompt_id != sticky_id:
        await _delete_chat_message(message=message, message_id=prompt_id)
    if drop_reply_kb:
        await _drop_reply_keyboard(message)


async def _finish_profile_flow(
        *,
        message: Message,
        state: FSMContext,
        user: User | None,
        i18n: dict[str, str],
        drop_reply_kb: bool = False,
) -> None:
    """Remove FSM prompts/aux and restore sticky hub when possible."""
    await _cleanup_profile_messages(
        message=message,
        state=state,
        drop_reply_kb=drop_reply_kb,
    )
    await clear_state_keep_hub(state)
    if user is not None:
        await show_hub(
            message=message,
            user=user,
            i18n=i18n,
            state=state,
        )


async def _show_profile_prompt(
        *,
        message: Message,
        state: FSMContext,
        i18n: dict[str, str],
        text: str,
        with_phone_kb: bool = False,
) -> None:
    """
    Show the next FSM question on the sticky hub message when possible.
    Phone step also sends a short aux message that carries the reply keyboard.
    """
    data = await state.get_data()
    sticky_id = data.get(HUB_MESSAGE_ID_KEY)
    prompt_id = sticky_id or data.get(_PROFILE_PROMPT_ID_KEY)
    # Phone step already has reply-keyboard Cancel — no inline button.
    inline_kb = None if with_phone_kb else get_profile_cancel_kb(i18n)

    # Drop previous phone aux before replacing the prompt.
    await _delete_chat_message(
        message=message,
        message_id=data.get(_PROFILE_AUX_ID_KEY),
    )
    await state.update_data({_PROFILE_AUX_ID_KEY: None})

    edited = False
    if prompt_id is not None:
        try:
            await message.bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=prompt_id,
                text=text,
                reply_markup=inline_kb,
            )
            edited = True
        except TelegramBadRequest as exc:
            if _is_not_modified(exc):
                edited = True

    if not edited:
        sent = await message.answer(text=text, reply_markup=inline_kb)
        await state.update_data({_PROFILE_PROMPT_ID_KEY: sent.message_id})
    elif sticky_id is not None:
        await state.update_data({_PROFILE_PROMPT_ID_KEY: None})

    if with_phone_kb:
        aux = await message.answer(
            text=i18n.get("profile_share_phone_button"),
            reply_markup=get_phone_kb(i18n),
        )
        await state.update_data({_PROFILE_AUX_ID_KEY: aux.message_id})


async def _save_profile(
        *,
        message: Message,
        state: FSMContext,
        repos: Repositories,
        user: User | None,
        i18n: dict[str, str],
        phone: str,
) -> None:
    if user is None:
        await _cleanup_profile_messages(
            message=message,
            state=state,
            drop_reply_kb=True,
        )
        await clear_state_keep_hub(state)
        await message.answer(
            text=i18n.get("book_need_start"),
            reply_markup=remove_kb(),
        )
        return

    data = await state.get_data()
    await repos.users.update_profile(
        user_id=user.user_id,
        first_name=data["first_name"],
        last_name=data["last_name"],
        phone=phone,
    )
    resume_book = bool(data.get("resume_book"))
    if resume_book:
        await _cleanup_profile_messages(
            message=message,
            state=state,
            drop_reply_kb=True,
        )
        await clear_state_keep_hub(state)
        await message.answer(
            text=i18n.get("profile_saved_continue_book"),
            reply_markup=remove_kb(),
        )
        return

    await _finish_profile_flow(
        message=message,
        state=state,
        user=user,
        i18n=i18n,
        drop_reply_kb=True,
    )


async def start_profile_flow(
        *,
        message: Message,
        state: FSMContext,
        i18n: dict[str, str],
        resume_book: bool = False,
        edit: bool = False,
) -> None:
    data = await state.get_data()
    had_sticky = data.get(HUB_MESSAGE_ID_KEY) is not None
    await clear_state_keep_hub(state)
    await state.set_state(ProfileSG.first_name)
    updates: dict[str, object] = {"resume_book": resume_book}
    if edit and not had_sticky:
        # Hub leaf without stored id: treat this message as sticky.
        updates[HUB_MESSAGE_ID_KEY] = message.message_id
    await state.update_data(updates)

    await _show_profile_prompt(
        message=message,
        state=state,
        i18n=i18n,
        text=i18n.get("profile_ask_first_name"),
    )


@profile_router.message(Command(commands="profile"))
async def process_profile_command(
        message: Message,
        state: FSMContext,
        user: User | None,
        i18n: dict[str, str],
) -> None:
    if user is None:
        await message.answer(text=i18n.get("book_need_start"))
        return

    if user.profile_complete:
        await clear_state_keep_hub(state)
        await message.answer(text=format_profile_card(user, i18n))
        await message.answer(text=i18n.get("profile_edit_hint"))
        return

    await start_profile_flow(
        message=message,
        state=state,
        i18n=i18n,
        resume_book=False,
    )


@profile_router.message(Command(commands="edit_profile"))
async def process_edit_profile_command(
        message: Message,
        state: FSMContext,
        user: User | None,
        i18n: dict[str, str],
) -> None:
    if user is None:
        await message.answer(text=i18n.get("book_need_start"))
        return
    await start_profile_flow(
        message=message,
        state=state,
        i18n=i18n,
        resume_book=False,
    )


@profile_router.message(Command(commands="cancel"), StateFilter(ProfileSG))
async def process_profile_cancel_cmd(
        message: Message,
        state: FSMContext,
        user: User | None,
        i18n: dict[str, str],
) -> None:
    drop_reply_kb = await state.get_state() == ProfileSG.phone.state
    await _delete_user_input(message)
    await _finish_profile_flow(
        message=message,
        state=state,
        user=user,
        i18n=i18n,
        drop_reply_kb=drop_reply_kb,
    )


@profile_router.callback_query(
    StateFilter(ProfileSG),
    ProfileNavCallback.filter(F.action == "cancel"),
)
async def process_profile_cancel_cb(
        callback: CallbackQuery,
        state: FSMContext,
        user: User | None,
        i18n: dict[str, str],
) -> None:
    await callback.answer()
    drop_reply_kb = await state.get_state() == ProfileSG.phone.state
    await _finish_profile_flow(
        message=callback.message,
        state=state,
        user=user,
        i18n=i18n,
        drop_reply_kb=drop_reply_kb,
    )


@profile_router.message(
    StateFilter(ProfileSG.first_name),
    F.text,
    ~F.text.startswith("/"),
)
async def process_first_name(
        message: Message,
        state: FSMContext,
        i18n: dict[str, str],
) -> None:
    first_name = (message.text or "").strip()
    await _delete_user_input(message)
    if len(first_name) < 2:
        await _show_profile_prompt(
            message=message,
            state=state,
            i18n=i18n,
            text=i18n.get("profile_invalid_name"),
        )
        return
    await state.update_data(first_name=first_name)
    await state.set_state(ProfileSG.last_name)
    await _show_profile_prompt(
        message=message,
        state=state,
        i18n=i18n,
        text=i18n.get("profile_ask_last_name"),
    )


@profile_router.message(
    StateFilter(ProfileSG.last_name),
    F.text,
    ~F.text.startswith("/"),
)
async def process_last_name(
        message: Message,
        state: FSMContext,
        i18n: dict[str, str],
) -> None:
    last_name = (message.text or "").strip()
    await _delete_user_input(message)
    if len(last_name) < 2:
        await _show_profile_prompt(
            message=message,
            state=state,
            i18n=i18n,
            text=i18n.get("profile_invalid_name"),
        )
        return
    await state.update_data(last_name=last_name)
    await state.set_state(ProfileSG.phone)
    await _show_profile_prompt(
        message=message,
        state=state,
        i18n=i18n,
        text=i18n.get("profile_ask_phone"),
        with_phone_kb=True,
    )


@profile_router.message(StateFilter(ProfileSG.phone), F.contact)
async def process_phone_contact(
        message: Message,
        state: FSMContext,
        repos: Repositories,
        user: User | None,
        i18n: dict[str, str],
) -> None:
    contact = message.contact
    phone = contact.phone_number if contact else None
    contact_user_id = contact.user_id if contact else None
    await _delete_user_input(message)

    if not phone:
        await _show_profile_prompt(
            message=message,
            state=state,
            i18n=i18n,
            text=i18n.get("profile_invalid_phone"),
            with_phone_kb=True,
        )
        return

    if user is not None and contact_user_id and contact_user_id != user.user_id:
        await _show_profile_prompt(
            message=message,
            state=state,
            i18n=i18n,
            text=i18n.get("profile_invalid_phone"),
            with_phone_kb=True,
        )
        return

    await _save_profile(
        message=message,
        state=state,
        repos=repos,
        user=user,
        i18n=i18n,
        phone=phone,
    )


@profile_router.message(
    StateFilter(ProfileSG.phone),
    F.text,
    ~F.text.startswith("/"),
)
async def process_phone_text(
        message: Message,
        state: FSMContext,
        repos: Repositories,
        user: User | None,
        i18n: dict[str, str],
) -> None:
    raw = (message.text or "").strip()
    await _delete_user_input(message)
    if raw == i18n.get("profile_cancel_button"):
        await _finish_profile_flow(
            message=message,
            state=state,
            user=user,
            i18n=i18n,
            drop_reply_kb=True,
        )
        return

    phone = raw.replace(" ", "").replace("-", "")
    if not _PHONE_RE.match(phone):
        await _show_profile_prompt(
            message=message,
            state=state,
            i18n=i18n,
            text=i18n.get("profile_invalid_phone"),
            with_phone_kb=True,
        )
        return

    await _save_profile(
        message=message,
        state=state,
        repos=repos,
        user=user,
        i18n=i18n,
        phone=phone,
    )


async def _hub_profile_show(
        *,
        message: Message,
        user: User,
        i18n: dict[str, str],
        state: FSMContext,
        **_,
) -> None:
    if user.role != UserRole.CLIENT:
        return
    await state.update_data(hub_screen="profile_show", hub_back="profile")
    if not user.profile_complete:
        await start_profile_flow(
            message=message,
            state=state,
            i18n=i18n,
            resume_book=False,
            edit=True,
        )
        return
    await message.edit_text(
        text=format_profile_card(user, i18n),
        reply_markup=get_hub_back_home_kb(i18n),
    )


async def _hub_profile_edit(
        *,
        message: Message,
        user: User,
        i18n: dict[str, str],
        state: FSMContext,
        **_,
) -> None:
    if user.role != UserRole.CLIENT:
        return
    await state.update_data(hub_screen="profile_edit", hub_back="profile")
    await start_profile_flow(
        message=message,
        state=state,
        i18n=i18n,
        resume_book=False,
        edit=True,
    )


register("profile_show", _hub_profile_show)
register("profile_edit", _hub_profile_edit)
