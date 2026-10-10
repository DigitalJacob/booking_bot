"""Profile / PDN consent entry points (no dependency on booking handlers)."""

from contextlib import suppress

from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, Message

from app.bot.keyboards.profile import (
    get_phone_kb,
    get_profile_cancel_kb,
    get_profile_consent_kb,
    remove_kb,
)
from app.bot.states.states import ProfileSG
from app.bot.utils.hub_nav import HUB_MESSAGE_ID_KEY, clear_state_keep_hub, show_hub
from app.domain.models import User

_PROFILE_PROMPT_ID_KEY = "profile_prompt_message_id"
_PROFILE_AUX_ID_KEY = "profile_aux_message_id"


def _is_not_modified(exc: TelegramBadRequest) -> bool:
    return "message is not modified" in str(exc).lower()


async def _delete_chat_message(
        *,
        message: Message,
        message_id: int | None,
) -> None:
    if message_id is None:
        return
    with suppress(TelegramBadRequest):
        await message.bot.delete_message(
            chat_id=message.chat.id,
            message_id=message_id,
        )


async def delete_user_input(message: Message) -> None:
    """Delete the client's chat message after its content was read."""
    await _delete_chat_message(message=message, message_id=message.message_id)


async def _drop_reply_keyboard(message: Message) -> None:
    """Remove reply keyboard without leaving a visible notice in chat."""
    stub = await message.answer(text=".", reply_markup=remove_kb())
    with suppress(TelegramBadRequest):
        await stub.delete()


async def cleanup_profile_messages(
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


async def finish_profile_flow(
        *,
        message: Message,
        state: FSMContext,
        user: User | None,
        i18n: dict[str, str],
        drop_reply_kb: bool = False,
) -> None:
    """Remove FSM prompts/aux and restore sticky hub when possible."""
    await cleanup_profile_messages(
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


def _consent_text(
        *,
        i18n: dict[str, str],
        operator_name: str,
        operator_contacts: str,
) -> str:
    return i18n.get("profile_consent_text").format(
        operator_name=operator_name or i18n.get("profile_pdn_operator_fallback"),
        operator_contacts=(
            operator_contacts or i18n.get("profile_pdn_contacts_fallback")
        ),
    )


async def show_profile_prompt(
        *,
        message: Message,
        state: FSMContext,
        i18n: dict[str, str],
        text: str,
        with_phone_kb: bool = False,
        reply_markup: InlineKeyboardMarkup | None = None,
) -> None:
    """
    Show the next FSM question on the sticky hub message when possible.
    Phone step also sends a short aux message that carries the reply keyboard.
    """
    data = await state.get_data()
    sticky_id = data.get(HUB_MESSAGE_ID_KEY)
    prompt_id = sticky_id or data.get(_PROFILE_PROMPT_ID_KEY)
    # Phone step already has reply-keyboard Cancel — no inline button.
    if with_phone_kb:
        inline_kb = None
    elif reply_markup is not None:
        inline_kb = reply_markup
    else:
        inline_kb = get_profile_cancel_kb(i18n)

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


async def begin_profile_fields(
        *,
        message: Message,
        state: FSMContext,
        i18n: dict[str, str],
        resume_book: bool,
) -> None:
    await state.set_state(ProfileSG.first_name)
    intro_key = (
        "profile_intro_book" if resume_book else "profile_intro_edit"
    )
    await show_profile_prompt(
        message=message,
        state=state,
        i18n=i18n,
        text=i18n.get(intro_key),
    )


async def start_profile_flow(
        *,
        message: Message,
        state: FSMContext,
        i18n: dict[str, str],
        user: User,
        pdn_consent_version: str,
        pdn_operator_name: str = "",
        pdn_operator_contacts: str = "",
        pdn_policy_url: str = "",
        resume_book: bool = False,
        edit: bool = False,
) -> None:
    data = await state.get_data()
    had_sticky = data.get(HUB_MESSAGE_ID_KEY) is not None
    await clear_state_keep_hub(state)
    updates: dict[str, object] = {
        "resume_book": resume_book,
        "pdn_consent_version": pdn_consent_version,
    }
    if edit and not had_sticky:
        # Hub leaf without stored id: treat this message as sticky.
        updates[HUB_MESSAGE_ID_KEY] = message.message_id
    await state.update_data(updates)

    if user.has_pdn_consent(version=pdn_consent_version):
        await begin_profile_fields(
            message=message,
            state=state,
            i18n=i18n,
            resume_book=resume_book,
        )
        return

    await state.set_state(ProfileSG.consent)
    await show_profile_prompt(
        message=message,
        state=state,
        i18n=i18n,
        text=_consent_text(
            i18n=i18n,
            operator_name=pdn_operator_name,
            operator_contacts=pdn_operator_contacts,
        ),
        reply_markup=get_profile_consent_kb(
            i18n=i18n,
            policy_url=pdn_policy_url,
        ),
    )
