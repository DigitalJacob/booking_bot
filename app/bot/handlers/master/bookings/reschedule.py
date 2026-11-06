"""Master reschedule funnel from the bookings card."""

from __future__ import annotations

from datetime import datetime

from aiogram import Bot, F
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

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
from app.bot.handlers.master.bookings.actions import (
    reject_if_slot_past,
    show_booking_card,
)
from app.bot.handlers.master.bookings.router import bookings_router
from app.bot.keyboards.booking import (
    BookingNavCallback,
    DayCallback,
    DayPadCallback,
    MonthCallback,
    WindowCallback,
)
from app.bot.keyboards.bookings import MasterRescheduleCallback, get_master_late_kb
from app.bot.states.states import MasterRescheduleSG
from app.bot.utils.format import format_dt
from app.bot.utils.notify import notify_appointment
from app.domain.exceptions import (
    AppointmentAlreadyEnded,
    AppointmentNotFound,
    ForbiddenBookingAction,
    InvalidAppointmentStatus,
    RescheduleSameTime,
    TimeConflict,
    WindowNotAvailable,
)
from app.domain.models import User
from app.domain.services.booking import BookingService
from app.infrastructure.database.repositories import Repositories

_FUNNEL_STATES = StateFilter(
    MasterRescheduleSG.choosing_month,
    MasterRescheduleSG.choosing_day,
    MasterRescheduleSG.choosing_window,
    MasterRescheduleSG.confirming,
)


async def _load_owned_appointment(
    *,
    repos: Repositories,
    appointment_id: int,
    master_user_id: int,
):
    appointment = await repos.appointments.get_appointment(
        appointment_id=appointment_id,
    )
    if appointment is None or appointment.master_user_id != master_user_id:
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
        master_user_id=user.user_id,
    )
    if appointment is None:
        return
    await show_booking_card(
        message=message,
        state=state,
        appointment=appointment,
        repos=repos,
        i18n=i18n,
        bot_timezone=bot_timezone,
    )


@bookings_router.callback_query(MasterRescheduleCallback.filter(F.action == "start"))
async def process_reschedule_start(
    callback: CallbackQuery,
    callback_data: MasterRescheduleCallback,
    state: FSMContext,
    repos: Repositories,
    user: User,
    i18n: dict[str, str],
    bot_timezone: str,
    schedule_mode: str,
) -> None:
    if await reject_if_slot_past(
        callback=callback,
        repos=repos,
        appointment_id=callback_data.appointment_id,
        i18n=i18n,
    ):
        return

    appointment = await _load_owned_appointment(
        repos=repos,
        appointment_id=callback_data.appointment_id,
        master_user_id=user.user_id,
    )
    if appointment is None:
        await callback.answer(
            text=i18n.get("master_action_failed"),
            show_alert=True,
        )
        return

    started = await start_reschedule_funnel(
        message=callback.message,
        state=state,
        repos=repos,
        appointment=appointment,
        states=MasterRescheduleSG,
        for_master=True,
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


@bookings_router.callback_query(
    MonthCallback.filter(),
    StateFilter(MasterRescheduleSG.choosing_month),
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
        states=MasterRescheduleSG,
        for_master=True,
    )


@bookings_router.callback_query(
    DayPadCallback.filter(),
    StateFilter(MasterRescheduleSG.choosing_day),
)
async def process_reschedule_day_pad(callback: CallbackQuery) -> None:
    await callback.answer()


@bookings_router.callback_query(
    DayCallback.filter(),
    StateFilter(MasterRescheduleSG.choosing_day),
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
        states=MasterRescheduleSG,
        for_master=True,
    )


@bookings_router.callback_query(
    WindowCallback.filter(),
    StateFilter(MasterRescheduleSG.choosing_window),
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
        states=MasterRescheduleSG,
        for_master=True,
        confirm_header=header,
        confirm_key="reschedule_confirm",
        confirm_button_key="reschedule_confirm_button",
    )


@bookings_router.callback_query(
    BookingNavCallback.filter(F.action == "confirm"),
    StateFilter(MasterRescheduleSG.confirming),
)
async def process_reschedule_confirm(
    callback: CallbackQuery,
    bot: Bot,
    translations: dict,
    state: FSMContext,
    repos: Repositories,
    user: User,
    i18n: dict[str, str],
    bot_timezone: str,
    schedule_mode: str,
) -> None:
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
    except (
        AppointmentNotFound,
        ForbiddenBookingAction,
        InvalidAppointmentStatus,
        AppointmentAlreadyEnded,
        RescheduleSameTime,
    ):
        await callback.answer(
            text=i18n.get("master_action_failed"),
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
    if appointment.client_user_id is not None:
        await notify_appointment(
            bot=bot,
            repos=repos,
            appointment=appointment,
            recipient_user_id=appointment.client_user_id,
            translations=translations,
            text_key="client_booking_rescheduled",
            bot_timezone=bot_timezone,
            with_dismiss=True,
            extra={
                "old_when": format_dt(result.old_starts_at, bot_timezone),
            },
        )

    await clear_reschedule_state(state)
    await show_booking_card(
        message=callback.message,
        state=state,
        appointment=appointment,
        repos=repos,
        i18n=i18n,
        bot_timezone=bot_timezone,
    )
    await callback.answer(text=i18n.get("master_rescheduled_ok"))


@bookings_router.callback_query(
    BookingNavCallback.filter(F.action == "cancel"),
    _FUNNEL_STATES,
)
async def process_reschedule_cancel(
    callback: CallbackQuery,
    state: FSMContext,
    repos: Repositories,
    user: User,
    i18n: dict[str, str],
    bot_timezone: str,
) -> None:
    await _return_to_card(
        message=callback.message,
        state=state,
        repos=repos,
        user=user,
        i18n=i18n,
        bot_timezone=bot_timezone,
    )
    await callback.answer()


@bookings_router.callback_query(
    BookingNavCallback.filter(F.action == "back"),
    _FUNNEL_STATES,
)
async def process_reschedule_back(
    callback: CallbackQuery,
    state: FSMContext,
    repos: Repositories,
    user: User,
    i18n: dict[str, str],
    bot_timezone: str,
    schedule_mode: str,
) -> None:
    current = await state.get_state()
    if current == MasterRescheduleSG.choosing_month.state:
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
        states=MasterRescheduleSG,
        for_master=True,
        has_service_step=False,
    )


@bookings_router.message(_FUNNEL_STATES, F.text)
async def process_reschedule_text(
    message: Message,
    i18n: dict[str, str],
) -> None:
    await message.answer(text=i18n.get("book_use_buttons"))


@bookings_router.callback_query(MasterRescheduleCallback.filter(F.action == "late"))
async def process_late_prompt(
    callback: CallbackQuery,
    callback_data: MasterRescheduleCallback,
    repos: Repositories,
    user: User,
    i18n: dict[str, str],
) -> None:
    if await reject_if_slot_past(
        callback=callback,
        repos=repos,
        appointment_id=callback_data.appointment_id,
        i18n=i18n,
    ):
        return

    appointment = await _load_owned_appointment(
        repos=repos,
        appointment_id=callback_data.appointment_id,
        master_user_id=user.user_id,
    )
    if appointment is None:
        await callback.answer(
            text=i18n.get("master_action_failed"),
            show_alert=True,
        )
        return

    await callback.message.edit_text(
        text=i18n.get("master_late_prompt"),
        reply_markup=get_master_late_kb(
            appointment_id=appointment.id,
            i18n=i18n,
        ),
    )
    await callback.answer()


@bookings_router.callback_query(MasterRescheduleCallback.filter(F.action == "late_back"))
async def process_late_back(
    callback: CallbackQuery,
    callback_data: MasterRescheduleCallback,
    state: FSMContext,
    repos: Repositories,
    user: User,
    i18n: dict[str, str],
    bot_timezone: str,
) -> None:
    appointment = await _load_owned_appointment(
        repos=repos,
        appointment_id=callback_data.appointment_id,
        master_user_id=user.user_id,
    )
    if appointment is None:
        await callback.answer(
            text=i18n.get("master_action_failed"),
            show_alert=True,
        )
        return

    await show_booking_card(
        message=callback.message,
        state=state,
        appointment=appointment,
        repos=repos,
        i18n=i18n,
        bot_timezone=bot_timezone,
    )
    await callback.answer()


@bookings_router.callback_query(MasterRescheduleCallback.filter(F.action == "shift"))
async def process_late_shift(
    callback: CallbackQuery,
    callback_data: MasterRescheduleCallback,
    bot: Bot,
    translations: dict,
    state: FSMContext,
    repos: Repositories,
    user: User,
    i18n: dict[str, str],
    bot_timezone: str,
    schedule_mode: str,
) -> None:
    if await reject_if_slot_past(
        callback=callback,
        repos=repos,
        appointment_id=callback_data.appointment_id,
        i18n=i18n,
    ):
        return

    appointment = await _load_owned_appointment(
        repos=repos,
        appointment_id=callback_data.appointment_id,
        master_user_id=user.user_id,
    )
    if appointment is None:
        await callback.answer(
            text=i18n.get("master_action_failed"),
            show_alert=True,
        )
        return

    booking = BookingService(repos)
    try:
        result = await booking.shift_late(
            appointment_id=callback_data.appointment_id,
            master_user_id=user.user_id,
            minutes=callback_data.minutes,
            schedule_mode=schedule_mode,
        )
    except WindowNotAvailable:
        await callback.answer(
            text=i18n.get("master_shift_unavailable"),
            show_alert=True,
        )
        return
    except (
        AppointmentNotFound,
        ForbiddenBookingAction,
        InvalidAppointmentStatus,
        AppointmentAlreadyEnded,
        ValueError,
    ):
        await callback.answer(
            text=i18n.get("master_action_failed"),
            show_alert=True,
        )
        return

    appointment = result.appointment
    if appointment.client_user_id is not None:
        await notify_appointment(
            bot=bot,
            repos=repos,
            appointment=appointment,
            recipient_user_id=appointment.client_user_id,
            translations=translations,
            text_key="client_booking_shifted",
            bot_timezone=bot_timezone,
            with_dismiss=True,
            extra={
                "old_when": format_dt(result.old_starts_at, bot_timezone),
            },
        )

    await show_booking_card(
        message=callback.message,
        state=state,
        appointment=appointment,
        repos=repos,
        i18n=i18n,
        bot_timezone=bot_timezone,
    )
    await callback.answer(
        text=format_dt(appointment.starts_at, bot_timezone),
    )
