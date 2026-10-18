"""Service choice step and hub entry for client booking."""

from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.bot.handlers.client.booking.common import (
    bookable_months,
    show_months,
    unique_days,
)
from app.bot.handlers.client.booking.router import booking_router
from app.bot.handlers.client.booking_flow import start_booking_flow
from app.bot.keyboards.booking import ServiceCallback
from app.bot.states.states import BookingSG
from app.bot.utils.hub_registry import register
from app.domain.enums import UserRole
from app.domain.models import User
from app.domain.services.booking import BookingService
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
    fsm_data = await state.get_data()
    master_user_id = fsm_data["master_user_id"]

    service = await repos.services.get_service(service_id=callback_data.service_id)
    if service is None or service.master_user_id != master_user_id or not service.is_active:
        await callback.answer(
            text=i18n.get("book_service_not_found"),
            show_alert=True,
        )
        return

    booking = BookingService(repos)
    open_months = await booking.list_open_months(
        master_user_id=master_user_id,
        schedule_mode=schedule_mode,
    )
    windows = await booking.list_available_windows(
        master_user_id=master_user_id,
        duration_minutes=service.duration_minutes,
        schedule_mode=schedule_mode,
    )
    days = unique_days(windows, bot_timezone)
    months = bookable_months(open_months, days)
    if not months:
        await callback.answer(
            text=i18n.get("book_no_windows"),
            show_alert=True,
        )
        return

    await state.update_data(
        service_id=service.id,
        service_duration=service.duration_minutes,
        book_year=None,
        book_month=None,
    )
    await state.set_state(BookingSG.choosing_month)
    await show_months(message=callback.message, months=months, i18n=i18n)
    await callback.answer()


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
