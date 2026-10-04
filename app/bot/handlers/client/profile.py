import re

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.bot.handlers.client.booking_flow import resume_booking_after_profile
from app.bot.handlers.client.profile_flow import (
    begin_profile_fields,
    cleanup_profile_messages,
    delete_user_input,
    finish_profile_flow,
    show_profile_prompt,
    start_profile_flow,
)
from app.bot.keyboards.hub import get_hub_back_home_kb
from app.bot.keyboards.profile import ProfileNavCallback, remove_kb
from app.bot.states.states import ProfileSG
from app.bot.utils.hub_nav import clear_state_keep_hub
from app.bot.utils.hub_registry import register
from app.domain.enums import UserRole
from app.domain.models import User
from app.infrastructure.database.repositories import Repositories


profile_router = Router(name="client_profile")

_PHONE_RE = re.compile(r"^\+?\d{10,15}$")


def format_profile_card(user: User, i18n: dict[str, str]) -> str:
    return i18n.get("profile_card").format(
        first_name=user.first_name or "-",
        last_name=user.last_name or "-",
        phone=user.phone or "-",
    )


async def _save_profile(
        *,
        message: Message,
        state: FSMContext,
        repos: Repositories,
        user: User | None,
        i18n: dict[str, str],
        phone: str,
        master_user_id: int,
        pdn_consent_version: str,
        pdn_operator_name: str,
        pdn_operator_contacts: str,
        pdn_policy_url: str,
) -> None:
    if user is None:
        await cleanup_profile_messages(
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
        await resume_booking_after_profile(
            message=message,
            state=state,
            repos=repos,
            user=user,
            i18n=i18n,
            master_user_id=master_user_id,
            pdn_consent_version=pdn_consent_version,
            pdn_operator_name=pdn_operator_name,
            pdn_operator_contacts=pdn_operator_contacts,
            pdn_policy_url=pdn_policy_url,
            drop_reply_kb=True,
        )
        return

    await finish_profile_flow(
        message=message,
        state=state,
        user=user,
        i18n=i18n,
        drop_reply_kb=True,
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
    await finish_profile_flow(
        message=callback.message,
        state=state,
        user=user,
        i18n=i18n,
        drop_reply_kb=drop_reply_kb,
    )


@profile_router.callback_query(
    StateFilter(ProfileSG.consent),
    ProfileNavCallback.filter(F.action == "consent_no"),
)
async def process_consent_no(
        callback: CallbackQuery,
        state: FSMContext,
        user: User | None,
        i18n: dict[str, str],
) -> None:
    await finish_profile_flow(
        message=callback.message,
        state=state,
        user=user,
        i18n=i18n,
    )
    await callback.answer(
        text=i18n.get("profile_consent_declined"),
        show_alert=True,
    )


@profile_router.callback_query(
    StateFilter(ProfileSG.consent),
    ProfileNavCallback.filter(F.action == "consent_yes"),
)
async def process_consent_yes(
        callback: CallbackQuery,
        state: FSMContext,
        repos: Repositories,
        user: User | None,
        i18n: dict[str, str],
        master_user_id: int,
        pdn_consent_version: str,
        pdn_operator_name: str,
        pdn_operator_contacts: str,
        pdn_policy_url: str,
) -> None:
    if user is None:
        await callback.answer(
            text=i18n.get("book_need_start"),
            show_alert=True,
        )
        await clear_state_keep_hub(state)
        return

    data = await state.get_data()
    version = data.get("pdn_consent_version") or pdn_consent_version
    await repos.users.set_pdn_consent(
        user_id=user.user_id,
        version=str(version),
    )
    resume_book = bool(data.get("resume_book"))
    refreshed = await repos.users.get_user_by_id(user_id=user.user_id)
    if refreshed is not None and refreshed.profile_complete:
        if resume_book:
            await resume_booking_after_profile(
                message=callback.message,
                state=state,
                repos=repos,
                user=refreshed,
                i18n=i18n,
                master_user_id=master_user_id,
                pdn_consent_version=pdn_consent_version,
                pdn_operator_name=pdn_operator_name,
                pdn_operator_contacts=pdn_operator_contacts,
                pdn_policy_url=pdn_policy_url,
            )
        else:
            await finish_profile_flow(
                message=callback.message,
                state=state,
                user=refreshed,
                i18n=i18n,
            )
        await callback.answer()
        return

    await begin_profile_fields(
        message=callback.message,
        state=state,
        i18n=i18n,
        resume_book=resume_book,
    )
    await callback.answer()


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
    await delete_user_input(message)
    if len(first_name) < 2:
        await show_profile_prompt(
            message=message,
            state=state,
            i18n=i18n,
            text=i18n.get("profile_invalid_name"),
        )
        return
    await state.update_data(first_name=first_name)
    await state.set_state(ProfileSG.last_name)
    await show_profile_prompt(
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
    await delete_user_input(message)
    if len(last_name) < 2:
        await show_profile_prompt(
            message=message,
            state=state,
            i18n=i18n,
            text=i18n.get("profile_invalid_name"),
        )
        return
    await state.update_data(last_name=last_name)
    await state.set_state(ProfileSG.phone)
    await show_profile_prompt(
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
        master_user_id: int,
        pdn_consent_version: str,
        pdn_operator_name: str,
        pdn_operator_contacts: str,
        pdn_policy_url: str,
) -> None:
    contact = message.contact
    phone = contact.phone_number if contact else None
    contact_user_id = contact.user_id if contact else None
    await delete_user_input(message)

    if not phone:
        await show_profile_prompt(
            message=message,
            state=state,
            i18n=i18n,
            text=i18n.get("profile_invalid_phone"),
            with_phone_kb=True,
        )
        return

    if user is not None and contact_user_id and contact_user_id != user.user_id:
        await show_profile_prompt(
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
        master_user_id=master_user_id,
        pdn_consent_version=pdn_consent_version,
        pdn_operator_name=pdn_operator_name,
        pdn_operator_contacts=pdn_operator_contacts,
        pdn_policy_url=pdn_policy_url,
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
        master_user_id: int,
        pdn_consent_version: str,
        pdn_operator_name: str,
        pdn_operator_contacts: str,
        pdn_policy_url: str,
) -> None:
    raw = (message.text or "").strip()
    await delete_user_input(message)
    if raw == i18n.get("profile_cancel_button"):
        await finish_profile_flow(
            message=message,
            state=state,
            user=user,
            i18n=i18n,
            drop_reply_kb=True,
        )
        return

    phone = raw.replace(" ", "").replace("-", "")
    if not _PHONE_RE.match(phone):
        await show_profile_prompt(
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
        master_user_id=master_user_id,
        pdn_consent_version=pdn_consent_version,
        pdn_operator_name=pdn_operator_name,
        pdn_operator_contacts=pdn_operator_contacts,
        pdn_policy_url=pdn_policy_url,
    )


async def _hub_profile_show(
        *,
        message: Message,
        user: User,
        i18n: dict[str, str],
        state: FSMContext,
        pdn_consent_version: str = "v1",
        pdn_operator_name: str = "",
        pdn_operator_contacts: str = "",
        pdn_policy_url: str = "",
        **_,
) -> None:
    if user.role != UserRole.CLIENT:
        return
    await state.update_data(hub_screen="profile_show", hub_back="profile")
    if (
        not user.profile_complete
        or not user.has_pdn_consent(version=pdn_consent_version)
    ):
        await start_profile_flow(
            message=message,
            state=state,
            i18n=i18n,
            user=user,
            pdn_consent_version=pdn_consent_version,
            pdn_operator_name=pdn_operator_name,
            pdn_operator_contacts=pdn_operator_contacts,
            pdn_policy_url=pdn_policy_url,
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
        pdn_consent_version: str = "v1",
        pdn_operator_name: str = "",
        pdn_operator_contacts: str = "",
        pdn_policy_url: str = "",
        **_,
) -> None:
    if user.role != UserRole.CLIENT:
        return
    await state.update_data(hub_screen="profile_edit", hub_back="profile")
    await start_profile_flow(
        message=message,
        state=state,
        i18n=i18n,
        user=user,
        pdn_consent_version=pdn_consent_version,
        pdn_operator_name=pdn_operator_name,
        pdn_operator_contacts=pdn_operator_contacts,
        pdn_policy_url=pdn_policy_url,
        resume_book=False,
        edit=True,
    )


register("profile_show", _hub_profile_show)
register("profile_edit", _hub_profile_edit)
