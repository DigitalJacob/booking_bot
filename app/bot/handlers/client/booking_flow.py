"""Booking entry / resume (depends on profile_flow, not on booking handlers)."""

from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.bot.handlers.client.profile_flow import (
    cleanup_profile_messages,
    start_profile_flow,
)
from app.bot.keyboards.booking import get_services_kb
from app.bot.keyboards.hub import get_hub_home_kb
from app.bot.states.states import BookingSG
from app.bot.utils.hub_nav import clear_state_keep_hub, show_hub_prompt
from app.domain.models import Service, User
from app.domain.services.booking import BookingService
from app.infrastructure.database.repositories import Repositories


async def _show_services(
        *,
        message: Message,
        state: FSMContext,
        services: list[Service],
        i18n: dict[str, str],
) -> None:
    await show_hub_prompt(
        message=message,
        state=state,
        text=i18n.get("book_choose_service"),
        reply_markup=get_services_kb(services=services, i18n=i18n),
    )


async def start_booking_flow(
        *,
        message: Message,
        i18n: dict[str, str],
        state: FSMContext,
        repos: Repositories,
        user: User,
        master_user_id: int,
        pdn_consent_version: str = "v1",
        pdn_operator_name: str = "",
        pdn_operator_contacts: str = "",
        pdn_policy_url: str = "",
        edit: bool = False,
) -> None:
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
            resume_book=True,
            edit=edit,
        )
        return

    await clear_state_keep_hub(state)

    booking = BookingService(repos)
    services = await booking.list_services(master_user_id=master_user_id)
    if not services:
        await show_hub_prompt(
            message=message,
            state=state,
            text=i18n.get("book_no_services"),
            reply_markup=get_hub_home_kb(i18n),
        )
        return

    await state.set_state(BookingSG.choosing_service)
    await state.update_data(master_user_id=master_user_id)
    await _show_services(
        message=message,
        state=state,
        services=services,
        i18n=i18n,
    )


async def resume_booking_after_profile(
        *,
        message: Message,
        state: FSMContext,
        repos: Repositories,
        user: User,
        i18n: dict[str, str],
        master_user_id: int,
        pdn_consent_version: str,
        pdn_operator_name: str,
        pdn_operator_contacts: str,
        pdn_policy_url: str,
        drop_reply_kb: bool = False,
) -> None:
    await cleanup_profile_messages(
        message=message,
        state=state,
        drop_reply_kb=drop_reply_kb,
    )
    await clear_state_keep_hub(state)
    refreshed = await repos.users.get_user_by_id(user_id=user.user_id)
    if refreshed is None:
        await message.answer(text=i18n.get("book_need_start"))
        return
    await start_booking_flow(
        message=message,
        i18n=i18n,
        state=state,
        repos=repos,
        user=refreshed,
        master_user_id=master_user_id,
        pdn_consent_version=pdn_consent_version,
        pdn_operator_name=pdn_operator_name,
        pdn_operator_contacts=pdn_operator_contacts,
        pdn_policy_url=pdn_policy_url,
        edit=False,
    )
