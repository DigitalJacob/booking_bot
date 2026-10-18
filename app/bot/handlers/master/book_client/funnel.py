"""Service → calendar → window → confirm for master book-for-client."""

from __future__ import annotations

from datetime import datetime

from aiogram import Bot, F
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.bot.handlers.common.booking_funnel import (
    handle_day_choice,
    handle_month_choice,
    handle_service_choice,
    handle_window_choice,
)
from app.bot.handlers.common.booking_nav import handle_booking_back
from app.bot.handlers.master.book_client.common import (
    cancel_book_client_flow,
    show_book_client_prompt,
)
from app.bot.handlers.master.book_client.router import book_client_router
from app.bot.keyboards.booking import (
    BookingNavCallback,
    DayCallback,
    DayPadCallback,
    MonthCallback,
    ServiceCallback,
    WindowCallback,
    get_services_kb,
)
from app.bot.keyboards.hub import get_hub_dismiss_kb
from app.bot.states.states import MasterBookSG
from app.bot.utils.contacts import client_contact
from app.bot.utils.hub_nav import clear_state_keep_hub, show_hub_prompt
from app.bot.utils.notify import notify_appointment
from app.domain.exceptions import (
    ForbiddenBookingAction,
    InvalidAppointmentClient,
    ManualClientNotFound,
    ServiceInactive,
    ServiceNotFound,
    TimeConflict,
    WindowNotAvailable,
)
from app.domain.models import User
from app.domain.services.booking import BookingService
from app.infrastructure.database.repositories import Repositories

_FUNNEL_STATES = StateFilter(
    MasterBookSG.choosing_service,
    MasterBookSG.choosing_month,
    MasterBookSG.choosing_day,
    MasterBookSG.choosing_window,
    MasterBookSG.confirming,
)


async def start_slot_funnel(
    *,
    message: Message,
    state: FSMContext,
    repos: Repositories,
    master_user_id: int,
    i18n: dict[str, str],
) -> bool:
    """Enter service choice. Returns False if the master has no services."""
    booking = BookingService(repos)
    services = await booking.list_services(master_user_id=master_user_id)
    if not services:
        await show_book_client_prompt(
            message=message,
            state=state,
            text=i18n.get("book_no_services"),
            i18n=i18n,
        )
        await clear_state_keep_hub(state)
        return False

    await state.update_data(
        master_user_id=master_user_id,
        service_id=None,
        service_duration=None,
        day=None,
        starts_at=None,
        book_year=None,
        book_month=None,
    )
    await state.set_state(MasterBookSG.choosing_service)
    # Sticky hub: inbound message may be deleted user text after New client.
    await show_hub_prompt(
        message=message,
        state=state,
        text=i18n.get("book_choose_service"),
        reply_markup=get_services_kb(services=services, i18n=i18n),
    )
    return True


async def _selected_client_header(
    *,
    repos: Repositories,
    state: FSMContext,
    master_user_id: int,
    i18n: dict[str, str],
) -> str:
    data = await state.get_data()
    kind = data.get("book_client_kind")
    ref_id = data.get("book_client_ref_id")
    if kind == "tg" and ref_id is not None:
        target = await repos.users.get_user_by_id(user_id=int(ref_id))
        if target is not None:
            name, phone = client_contact(target)
            return i18n.get("book_client_selected_line").format(
                client_name=name,
                client_phone=phone,
            )
    if kind == "manual" and ref_id is not None:
        manual = await repos.manual_clients.get(
            manual_client_id=int(ref_id),
            master_user_id=master_user_id,
        )
        if manual is not None:
            return i18n.get("book_client_selected_line").format(
                client_name=manual.name,
                client_phone=manual.phone,
            )
    return i18n.get("book_client_selected_line").format(
        client_name="?",
        client_phone="-",
    )


@book_client_router.message(_FUNNEL_STATES, F.text)
async def process_master_book_text(
    message: Message,
    i18n: dict[str, str],
) -> None:
    await message.answer(text=i18n.get("book_use_buttons"))


@book_client_router.callback_query(
    ServiceCallback.filter(),
    StateFilter(MasterBookSG.choosing_service),
)
async def process_master_service_choice(
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
        states=MasterBookSG,
        for_master=True,
    )


@book_client_router.callback_query(
    MonthCallback.filter(),
    StateFilter(MasterBookSG.choosing_month),
)
async def process_master_month_choice(
    callback: CallbackQuery,
    callback_data: MonthCallback,
    i18n: dict[str, str],
    state: FSMContext,
    repos: Repositories,
    bot_timezone: str,
    schedule_mode: str,
) -> None:
    await handle_month_choice(
        callback=callback,
        callback_data=callback_data,
        state=state,
        repos=repos,
        i18n=i18n,
        bot_timezone=bot_timezone,
        schedule_mode=schedule_mode,
        states=MasterBookSG,
        for_master=True,
    )


@book_client_router.callback_query(
    DayPadCallback.filter(),
    StateFilter(MasterBookSG.choosing_day),
)
async def process_master_day_pad(callback: CallbackQuery) -> None:
    await callback.answer()


@book_client_router.callback_query(
    DayCallback.filter(),
    StateFilter(MasterBookSG.choosing_day),
)
async def process_master_day_choice(
    callback: CallbackQuery,
    callback_data: DayCallback,
    i18n: dict[str, str],
    state: FSMContext,
    repos: Repositories,
    bot_timezone: str,
    schedule_mode: str,
) -> None:
    await handle_day_choice(
        callback=callback,
        callback_data=callback_data,
        state=state,
        repos=repos,
        i18n=i18n,
        bot_timezone=bot_timezone,
        schedule_mode=schedule_mode,
        states=MasterBookSG,
        for_master=True,
    )


@book_client_router.callback_query(
    WindowCallback.filter(),
    StateFilter(MasterBookSG.choosing_window),
)
async def process_master_window_choice(
    callback: CallbackQuery,
    callback_data: WindowCallback,
    i18n: dict[str, str],
    state: FSMContext,
    repos: Repositories,
    user: User,
    bot_timezone: str,
    schedule_mode: str,
) -> None:
    header = await _selected_client_header(
        repos=repos,
        state=state,
        master_user_id=user.user_id,
        i18n=i18n,
    )
    await handle_window_choice(
        callback=callback,
        callback_data=callback_data,
        state=state,
        repos=repos,
        i18n=i18n,
        bot_timezone=bot_timezone,
        schedule_mode=schedule_mode,
        states=MasterBookSG,
        for_master=True,
        confirm_header=header,
        confirm_button_key="book_client_confirm_button",
    )


@book_client_router.callback_query(
    BookingNavCallback.filter(F.action == "confirm"),
    StateFilter(MasterBookSG.confirming),
)
async def process_master_confirm(
    callback: CallbackQuery,
    bot: Bot,
    translations: dict,
    i18n: dict[str, str],
    state: FSMContext,
    repos: Repositories,
    user: User,
    bot_timezone: str,
    schedule_mode: str,
) -> None:
    fsm_data = await state.get_data()
    kind = fsm_data.get("book_client_kind")
    ref_id = fsm_data.get("book_client_ref_id")
    booking = BookingService(repos)

    client_user_id: int | None = None
    manual_client_id: int | None = None
    if kind == "tg" and ref_id is not None:
        client_user_id = int(ref_id)
    elif kind == "manual" and ref_id is not None:
        manual_client_id = int(ref_id)
    else:
        await callback.answer(
            text=i18n.get("book_client_target_lost"),
            show_alert=True,
        )
        await clear_state_keep_hub(state)
        return

    try:
        appointment = await booking.book_for_client(
            master_user_id=user.user_id,
            service_id=fsm_data["service_id"],
            starts_at=datetime.fromisoformat(fsm_data["starts_at"]),
            client_user_id=client_user_id,
            manual_client_id=manual_client_id,
            schedule_mode=schedule_mode,
        )
    except (TimeConflict, WindowNotAvailable):
        await callback.answer(text=i18n.get("book_window_taken"), show_alert=True)
        return
    except ServiceInactive:
        await callback.answer(
            text=i18n.get("book_service_inactive"),
            show_alert=True,
        )
        return
    except ServiceNotFound:
        await callback.answer(
            text=i18n.get("book_service_not_found"),
            show_alert=True,
        )
        return
    except (ForbiddenBookingAction, ManualClientNotFound, InvalidAppointmentClient):
        await callback.answer(
            text=i18n.get("book_client_target_lost"),
            show_alert=True,
        )
        await clear_state_keep_hub(state)
        return

    if appointment.client_user_id is not None:
        await notify_appointment(
            bot=bot,
            repos=repos,
            appointment=appointment,
            recipient_user_id=appointment.client_user_id,
            translations=translations,
            text_key="client_booked_by_master",
            bot_timezone=bot_timezone,
            with_dismiss=True,
        )

    await clear_state_keep_hub(state)
    await callback.message.edit_text(
        text=i18n.get("book_client_ok"),
        reply_markup=get_hub_dismiss_kb(i18n),
    )
    await callback.answer()


@book_client_router.callback_query(
    BookingNavCallback.filter(F.action == "cancel"),
    _FUNNEL_STATES,
)
async def process_master_funnel_cancel(
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


@book_client_router.callback_query(
    BookingNavCallback.filter(F.action == "back"),
    _FUNNEL_STATES,
)
async def process_master_funnel_back(
    callback: CallbackQuery,
    i18n: dict[str, str],
    state: FSMContext,
    repos: Repositories,
    bot_timezone: str,
    schedule_mode: str,
) -> None:
    await handle_booking_back(
        callback=callback,
        state=state,
        repos=repos,
        i18n=i18n,
        bot_timezone=bot_timezone,
        schedule_mode=schedule_mode,
        states=MasterBookSG,
        for_master=True,
    )
