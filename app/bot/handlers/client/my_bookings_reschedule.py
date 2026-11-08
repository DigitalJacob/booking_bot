"""Client reschedule funnel from My bookings."""

from __future__ import annotations

from datetime import UTC, datetime

from aiogram import Bot, F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.bot.handlers.client.my_bookings import show_my_booking_card
from app.bot.handlers.common.booking_funnel import (
    handle_day_choice,
    handle_month_choice,
    handle_window_choice,
)
from app.bot.handlers.common.booking_nav import handle_booking_back
from app.bot.handlers.common.booking_steps import (
    RESCHEDULE_APPOINTMENT_ID_KEY,
    RESCHEDULE_ORIGINAL_STARTS_AT_KEY,
)
from app.bot.handlers.common.reschedule_steps import (
    clear_reschedule_state,
    reschedule_confirm_header,
    start_reschedule_funnel,
)
from app.bot.keyboards.booking import (
    BookingNavCallback,
    DayCallback,
    DayPadCallback,
    MonthCallback,
    WindowCallback,
)
from app.bot.keyboards.my_bookings import ClientAppointmentCallback
from app.bot.states.states import ClientRescheduleSG
from app.bot.utils.format import format_dt
from app.bot.utils.notify import notify_appointment, supersede_master_action_push
from app.domain.exceptions import (
    AppointmentAlreadyEnded,
    AppointmentNotFound,
    ForbiddenBookingAction,
    InvalidAppointmentStatus,
    RescheduleSameTime,
    RescheduleTooLate,
    TimeConflict,
    WindowNotAvailable,
)
from app.domain.models import Appointment, User
from app.domain.services.booking import BookingService
from app.infrastructure.database.repositories import Repositories

my_bookings_reschedule_router = Router(name="client_my_bookings_reschedule")

_FUNNEL_STATES = StateFilter(
    ClientRescheduleSG.choosing_month,
    ClientRescheduleSG.choosing_day,
    ClientRescheduleSG.choosing_window,
    ClientRescheduleSG.confirming,
)


async def _load_owned_appointment(
    *,
    repos: Repositories,
    appointment_id: int,
    client_user_id: int,
) -> Appointment | None:
    appointment = await repos.appointments.get_appointment(
        appointment_id=appointment_id,
    )
    if appointment is None or appointment.client_user_id != client_user_id:
        return None
    return appointment


async def _return_to_card(
    *,
    message: Message,
    state: FSMContext,
    repos: Repositories,
    user: User,
    i18n: dict[str, str],
    bot_timezone: str,
    appointment_id: int | None = None,
) -> None:
    if appointment_id is None:
        data = await state.get_data()
        raw = data.get(RESCHEDULE_APPOINTMENT_ID_KEY)
        appointment_id = int(raw) if raw is not None else None
    await clear_reschedule_state(state)
    if appointment_id is None:
        return
    appointment = await _load_owned_appointment(
        repos=repos,
        appointment_id=appointment_id,
        client_user_id=user.user_id,
    )
    if appointment is None:
        return
    await show_my_booking_card(
        message=message,
        appointment=appointment,
        repos=repos,
        i18n=i18n,
        bot_timezone=bot_timezone,
    )


@my_bookings_reschedule_router.callback_query(
    ClientAppointmentCallback.filter(F.action == "reschedule"),
)
async def process_reschedule_start(
    callback: CallbackQuery,
    callback_data: ClientAppointmentCallback,
    state: FSMContext,
    repos: Repositories,
    user: User | None,
    i18n: dict[str, str],
    bot_timezone: str,
    schedule_mode: str,
) -> None:
    if user is None:
        await callback.answer(
            text=i18n.get("book_need_start"),
            show_alert=True,
        )
        return

    appointment = await _load_owned_appointment(
        repos=repos,
        appointment_id=callback_data.appointment_id,
        client_user_id=user.user_id,
    )
    if appointment is None:
        await callback.answer(
            text=i18n.get("my_bookings_action_failed"),
            show_alert=True,
        )
        return

    booking = BookingService(repos)
    min_lead = await booking.client_min_lead_minutes(
        master_user_id=appointment.master_user_id,
    )
    if booking.is_client_reschedule_too_late(
        starts_at=appointment.starts_at,
        min_lead_minutes=min_lead,
        now=datetime.now(UTC),
    ):
        await callback.answer(
            text=i18n.get("client_reschedule_too_late").format(minutes=min_lead),
            show_alert=True,
        )
        return

    started = await start_reschedule_funnel(
        message=callback.message,
        state=state,
        repos=repos,
        appointment=appointment,
        states=ClientRescheduleSG,
        for_master=False,
        i18n=i18n,
        bot_timezone=bot_timezone,
        schedule_mode=schedule_mode,
    )
    if not started:
        await callback.answer(
            text=i18n.get("reschedule_no_windows"),
            show_alert=True,
        )
        return
    await callback.answer()


@my_bookings_reschedule_router.callback_query(
    MonthCallback.filter(),
    StateFilter(ClientRescheduleSG.choosing_month),
)
async def process_reschedule_month(
    callback: CallbackQuery,
    callback_data: MonthCallback,
    state: FSMContext,
    repos: Repositories,
    i18n: dict[str, str],
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
        states=ClientRescheduleSG,
        for_master=False,
    )


@my_bookings_reschedule_router.callback_query(
    DayPadCallback.filter(),
    StateFilter(ClientRescheduleSG.choosing_day),
)
async def process_reschedule_day_pad(callback: CallbackQuery) -> None:
    await callback.answer()


@my_bookings_reschedule_router.callback_query(
    DayCallback.filter(),
    StateFilter(ClientRescheduleSG.choosing_day),
)
async def process_reschedule_day(
    callback: CallbackQuery,
    callback_data: DayCallback,
    state: FSMContext,
    repos: Repositories,
    i18n: dict[str, str],
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
        states=ClientRescheduleSG,
        for_master=False,
    )


@my_bookings_reschedule_router.callback_query(
    WindowCallback.filter(),
    StateFilter(ClientRescheduleSG.choosing_window),
)
async def process_reschedule_window(
    callback: CallbackQuery,
    callback_data: WindowCallback,
    state: FSMContext,
    repos: Repositories,
    i18n: dict[str, str],
    bot_timezone: str,
    schedule_mode: str,
) -> None:
    fsm_data = await state.get_data()
    original = fsm_data.get(RESCHEDULE_ORIGINAL_STARTS_AT_KEY)
    header = None
    if original:
        header = reschedule_confirm_header(
            old_starts_at=datetime.fromisoformat(original),
            i18n=i18n,
            bot_timezone=bot_timezone,
        )
    await handle_window_choice(
        callback=callback,
        callback_data=callback_data,
        state=state,
        repos=repos,
        i18n=i18n,
        bot_timezone=bot_timezone,
        schedule_mode=schedule_mode,
        states=ClientRescheduleSG,
        for_master=False,
        confirm_header=header,
        confirm_key="reschedule_confirm",
        confirm_button_key="reschedule_confirm_button",
    )


@my_bookings_reschedule_router.callback_query(
    BookingNavCallback.filter(F.action == "confirm"),
    StateFilter(ClientRescheduleSG.confirming),
)
async def process_reschedule_confirm(
    callback: CallbackQuery,
    bot: Bot,
    translations: dict,
    state: FSMContext,
    repos: Repositories,
    user: User | None,
    i18n: dict[str, str],
    bot_timezone: str,
    schedule_mode: str,
) -> None:
    if user is None:
        await callback.answer(
            text=i18n.get("book_need_start"),
            show_alert=True,
        )
        await clear_reschedule_state(state)
        return

    fsm_data = await state.get_data()
    appointment_id = int(fsm_data[RESCHEDULE_APPOINTMENT_ID_KEY])
    starts_at = datetime.fromisoformat(fsm_data["starts_at"])
    booking = BookingService(repos)

    try:
        result = await booking.reschedule(
            appointment_id=appointment_id,
            actor_user_id=user.user_id,
            new_starts_at=starts_at,
            schedule_mode=schedule_mode,
        )
    except (WindowNotAvailable, TimeConflict):
        await callback.answer(
            text=i18n.get("book_window_taken"),
            show_alert=True,
        )
        return
    except RescheduleTooLate:
        min_lead = await booking.client_min_lead_minutes(
            master_user_id=int(fsm_data["master_user_id"]),
        )
        await callback.answer(
            text=i18n.get("client_reschedule_too_late").format(minutes=min_lead),
            show_alert=True,
        )
        await _return_to_card(
            message=callback.message,
            state=state,
            repos=repos,
            user=user,
            i18n=i18n,
            bot_timezone=bot_timezone,
            appointment_id=appointment_id,
        )
        return
    except (
        AppointmentNotFound,
        ForbiddenBookingAction,
        InvalidAppointmentStatus,
        AppointmentAlreadyEnded,
        RescheduleSameTime,
    ):
        await callback.answer(
            text=i18n.get("my_bookings_action_failed"),
            show_alert=True,
        )
        await _return_to_card(
            message=callback.message,
            state=state,
            repos=repos,
            user=user,
            i18n=i18n,
            bot_timezone=bot_timezone,
            appointment_id=appointment_id,
        )
        return

    appointment = result.appointment
    if appointment.master_notify_message_id is not None:
        await supersede_master_action_push(
            bot=bot,
            repos=repos,
            appointment=appointment,
            translations=translations,
            text_key="master_push_rescheduled",
            bot_timezone=bot_timezone,
        )

    notify_msg_id = await notify_appointment(
        bot=bot,
        repos=repos,
        appointment=appointment,
        recipient_user_id=appointment.master_user_id,
        translations=translations,
        text_key="master_booking_rescheduled",
        bot_timezone=bot_timezone,
        with_master_actions=True,
        extra={
            "old_when": format_dt(result.old_starts_at, bot_timezone),
        },
    )
    if notify_msg_id is not None:
        await repos.appointments.set_master_notify_message_id(
            appointment_id=appointment.id,
            message_id=notify_msg_id,
        )

    await clear_reschedule_state(state)
    await show_my_booking_card(
        message=callback.message,
        appointment=appointment,
        repos=repos,
        i18n=i18n,
        bot_timezone=bot_timezone,
    )
    await callback.answer(text=i18n.get("client_rescheduled_ok"))


@my_bookings_reschedule_router.callback_query(
    BookingNavCallback.filter(F.action == "cancel"),
    _FUNNEL_STATES,
)
async def process_reschedule_cancel(
    callback: CallbackQuery,
    state: FSMContext,
    repos: Repositories,
    user: User | None,
    i18n: dict[str, str],
    bot_timezone: str,
) -> None:
    if user is None:
        await clear_reschedule_state(state)
        await callback.answer()
        return
    await _return_to_card(
        message=callback.message,
        state=state,
        repos=repos,
        user=user,
        i18n=i18n,
        bot_timezone=bot_timezone,
    )
    await callback.answer()


@my_bookings_reschedule_router.callback_query(
    BookingNavCallback.filter(F.action == "back"),
    _FUNNEL_STATES,
)
async def process_reschedule_back(
    callback: CallbackQuery,
    state: FSMContext,
    repos: Repositories,
    user: User | None,
    i18n: dict[str, str],
    bot_timezone: str,
    schedule_mode: str,
) -> None:
    current = await state.get_state()
    if current == ClientRescheduleSG.choosing_month.state:
        if user is None:
            await clear_reschedule_state(state)
            await callback.answer()
            return
        await _return_to_card(
            message=callback.message,
            state=state,
            repos=repos,
            user=user,
            i18n=i18n,
            bot_timezone=bot_timezone,
        )
        await callback.answer()
        return

    await handle_booking_back(
        callback=callback,
        state=state,
        repos=repos,
        i18n=i18n,
        bot_timezone=bot_timezone,
        schedule_mode=schedule_mode,
        states=ClientRescheduleSG,
        for_master=False,
        has_service_step=False,
    )


@my_bookings_reschedule_router.message(_FUNNEL_STATES, F.text)
async def process_reschedule_text(
    message: Message,
    i18n: dict[str, str],
) -> None:
    await message.answer(text=i18n.get("book_use_buttons"))
