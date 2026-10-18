"""Service choice step and hub entry for client booking."""

from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.bot.handlers.client.booking.router import booking_router
from app.bot.handlers.client.booking_flow import start_booking_flow
from app.bot.handlers.common.booking_funnel import handle_service_choice
from app.bot.keyboards.booking import ServiceCallback
from app.bot.states.states import BookingSG
from app.bot.utils.hub_registry import register
from app.domain.enums import UserRole
from app.domain.models import User
from app.infrastructure.database.repositories import Repositories


@booking_router.callback_query(
    ServiceCallback.filter(),
    StateFilter(BookingSG.choosing_service),
)
async def process_service_choice(
    callback: CallbackQuery,
    callback_data: ServiceCallback,
    i18n: dict[str, str],
    state: FSMContext,
    repos: Repositories,
    bot_timezone: str,
    schedule_mode: str,
) -> None:
    await handle_service_choice(
        callback=callback,
        callback_data=callback_data,
        state=state,
        repos=repos,
        i18n=i18n,
        bot_timezone=bot_timezone,
        schedule_mode=schedule_mode,
        states=BookingSG,
    )


async def _hub_book(
    *,
    message: Message,
    user: User,
    i18n: dict[str, str],
    state: FSMContext,
    repos: Repositories | None = None,
    master_user_id: int | None = None,
    pdn_consent_version: str = "v1",
    pdn_operator_name: str = "",
    pdn_operator_contacts: str = "",
    pdn_policy_url: str = "",
    **_,
) -> None:
    if user.role != UserRole.CLIENT or repos is None or master_user_id is None:
        return
    await state.update_data(hub_screen="book", hub_back="root")
    await start_booking_flow(
        message=message,
        i18n=i18n,
        state=state,
        repos=repos,
        user=user,
        master_user_id=master_user_id,
        pdn_consent_version=pdn_consent_version,
        pdn_operator_name=pdn_operator_name,
        pdn_operator_contacts=pdn_operator_contacts,
        pdn_policy_url=pdn_policy_url,
        edit=True,
    )


register("book", _hub_book)
