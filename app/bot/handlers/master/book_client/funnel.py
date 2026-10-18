"""Service → calendar → window → confirm for master book-for-client."""

from __future__ import annotations

from datetime import date, datetime

from aiogram import Bot, F
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.bot.handlers.common.booking_nav import handle_booking_back
from app.bot.handlers.common.booking_steps import (
    bookable_months,
    days_in_month,
    show_confirm,
    show_days,
    show_months,
    show_windows,
    unique_days,
    windows_on_day,
)
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
    get_confirm_kb,
    get_services_kb,
)
from app.bot.keyboards.hub import get_hub_dismiss_kb
from app.bot.states.states import MasterBookSG
from app.bot.utils.format import client_contact
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
    windows = await booking.list_windows_for_master(
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
    await state.set_state(MasterBookSG.choosing_month)
    await show_months(message=callback.message, months=months, i18n=i18n)
    await callback.answer()


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
    fsm_data = await state.get_data()
    master_user_id = fsm_data["master_user_id"]
    service_duration = fsm_data["service_duration"]

    booking = BookingService(repos)
    open_months = await booking.list_open_months(
        master_user_id=master_user_id,
        schedule_mode=schedule_mode,
    )
    windows = await booking.list_windows_for_master(
        master_user_id=master_user_id,
        duration_minutes=service_duration,
        schedule_mode=schedule_mode,
    )
    days = days_in_month(
        unique_days(windows, bot_timezone),
        callback_data.year,
        callback_data.month,
    )
    if (callback_data.year, callback_data.month) not in open_months or not days:
        await callback.answer(
            text=i18n.get("book_month_unavailable"),
            show_alert=True,
        )
        return

    await state.update_data(
        book_year=callback_data.year,
        book_month=callback_data.month,
    )
    await state.set_state(MasterBookSG.choosing_day)
    await show_days(
        message=callback.message,
        year=callback_data.year,
        month=callback_data.month,
        days=days,
        i18n=i18n,
    )
    await callback.answer()


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
    fsm_data = await state.get_data()
    master_user_id = fsm_data["master_user_id"]
    service_duration = fsm_data["service_duration"]
    day = date.fromisoformat(callback_data.value)
    book_year = fsm_data.get("book_year")
    book_month = fsm_data.get("book_month")
    if (
        book_year is not None
        and book_month is not None
        and (day.year, day.month) != (int(book_year), int(book_month))
    ):
        await callback.answer()
        return

    booking = BookingService(repos)
    windows = windows_on_day(
        await booking.list_windows_for_master(
            master_user_id=master_user_id,
            duration_minutes=service_duration,
            schedule_mode=schedule_mode,
        ),
        day,
        bot_timezone,
    )
    if not windows:
        await callback.answer(
            text=i18n.get("book_no_windows"),
            show_alert=True,
        )
        return

    await state.update_data(day=day.isoformat())
    await state.set_state(MasterBookSG.choosing_window)
    await show_windows(
        message=callback.message,
        windows=windows,
        i18n=i18n,
        bot_timezone=bot_timezone,
    )
    await callback.answer()


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
    fsm_data = await state.get_data()
    master_user_id = fsm_data["master_user_id"]
    service_id = fsm_data["service_id"]
    day = date.fromisoformat(fsm_data["day"])
    starts_at = datetime.fromisoformat(callback_data.starts_at)

    service = await repos.services.get_service(service_id=service_id)
    if service is None:
        await callback.answer(
            text=i18n.get("book_service_not_found"),
            show_alert=True,
        )
        return

    booking = BookingService(repos)
    windows = windows_on_day(
        await booking.list_windows_for_master(
            master_user_id=master_user_id,
            duration_minutes=service.duration_minutes,
            schedule_mode=schedule_mode,
        ),
        day,
        bot_timezone,
    )
    match = next(
        (
            window
            for window in windows
            if window.starts_at == starts_at
            or window.starts_at.isoformat() == callback_data.starts_at
        ),
        None,
    )
    if match is None:
        await callback.answer(
            text=i18n.get("book_window_not_found"),
            show_alert=True,
        )
        return

    await state.update_data(starts_at=match.starts_at.isoformat())
    await state.set_state(MasterBookSG.confirming)
    header = await _selected_client_header(
        repos=repos,
        state=state,
        master_user_id=user.user_id,
        i18n=i18n,
    )
    await show_confirm(
        message=callback.message,
        service=service,
        starts_at=match.starts_at,
        i18n=i18n,
        bot_timezone=bot_timezone,
        header=header,
        reply_markup=get_confirm_kb(
            i18n=i18n,
            confirm_button_key="book_client_confirm_button",
        ),
    )
    await callback.answer()


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
