"""Confirm, cancel, back, and text catch-all for client booking."""

from datetime import date, datetime

from aiogram import Bot, F
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.bot.handlers.client.booking.common import (
    bookable_months,
    days_in_month,
    show_days,
    show_months,
    show_services,
    show_windows,
    unique_days,
    windows_on_day,
)
from app.bot.handlers.client.booking.router import booking_router
from app.bot.keyboards.booking import BookingNavCallback
from app.bot.keyboards.hub import get_hub_dismiss_kb
from app.bot.states.states import BookingSG
from app.bot.utils.hub_nav import clear_state_keep_hub, show_hub
from app.bot.utils.notify import notify_appointment
from app.domain.exceptions import (
    ServiceInactive,
    ServiceNotFound,
    TimeConflict,
    WindowNotAvailable,
)
from app.domain.models import User
from app.domain.services.booking import BookingService
from app.infrastructure.database.repositories import Repositories


@booking_router.message(StateFilter(BookingSG), F.text)
async def process_booking_text(
    message: Message,
    i18n: dict[str, str],
) -> None:
    await message.answer(text=i18n.get("book_use_buttons"))


@booking_router.callback_query(
    BookingNavCallback.filter(F.action == "confirm"),
    StateFilter(BookingSG.confirming),
)
async def process_confirm(
    callback: CallbackQuery,
    bot: Bot,
    translations: dict,
    i18n: dict[str, str],
    state: FSMContext,
    repos: Repositories,
    user: User | None,
    bot_timezone: str,
    schedule_mode: str,
) -> None:
    if user is None:
        await callback.answer(
            text=i18n.get("book_need_start"),
            show_alert=True,
        )
        await clear_state_keep_hub(state)
        return

    fsm_data = await state.get_data()
    booking = BookingService(repos)
    try:
        appointment = await booking.book_window(
            client_user_id=user.user_id,
            service_id=fsm_data["service_id"],
            starts_at=datetime.fromisoformat(fsm_data["starts_at"]),
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

    notify_msg_id = await notify_appointment(
        bot=bot,
        repos=repos,
        appointment=appointment,
        recipient_user_id=appointment.master_user_id,
        translations=translations,
        text_key="master_new_booking",
        with_master_actions=True,
        bot_timezone=bot_timezone,
    )
    if notify_msg_id is not None:
        await repos.appointments.set_master_notify_message_id(
            appointment_id=appointment.id,
            message_id=notify_msg_id,
        )
    await clear_state_keep_hub(state)
    await callback.message.edit_text(
        text=i18n.get("book_ok"),
        reply_markup=get_hub_dismiss_kb(i18n),
    )
    await callback.answer()


@booking_router.callback_query(
    BookingNavCallback.filter(F.action == "cancel"),
    StateFilter(BookingSG),
)
async def process_cancel(
    callback: CallbackQuery,
    i18n: dict[str, str],
    state: FSMContext,
    user: User | None,
) -> None:
    await clear_state_keep_hub(state)
    await show_hub(
        message=callback.message,
        user=user,
        i18n=i18n,
        state=state,
    )
    await callback.answer()


@booking_router.callback_query(
    BookingNavCallback.filter(F.action == "back"),
    StateFilter(BookingSG),
)
async def process_back(
    callback: CallbackQuery,
    i18n: dict[str, str],
    state: FSMContext,
    repos: Repositories,
    bot_timezone: str,
    schedule_mode: str,
) -> None:
    current = await state.get_state()
    fsm_data = await state.get_data()
    master_user_id = fsm_data["master_user_id"]
    booking = BookingService(repos)

    if current == BookingSG.choosing_month.state:
        services = await booking.list_services(master_user_id=master_user_id)
        await state.set_state(BookingSG.choosing_service)
        await state.update_data(
            service_id=None,
            day=None,
            starts_at=None,
            service_duration=None,
            book_year=None,
            book_month=None,
        )
        await show_services(
            message=callback.message,
            services=services,
            i18n=i18n,
            edit=True,
        )
        await callback.answer()
        return

    if current == BookingSG.choosing_day.state:
        open_months = await booking.list_open_months(
            master_user_id=master_user_id,
            schedule_mode=schedule_mode,
        )
        windows = await booking.list_available_windows(
            master_user_id=master_user_id,
            duration_minutes=fsm_data["service_duration"],
            schedule_mode=schedule_mode,
        )
        months = bookable_months(
            open_months,
            unique_days(windows, bot_timezone),
        )
        await state.set_state(BookingSG.choosing_month)
        await state.update_data(day=None, starts_at=None, book_year=None, book_month=None)
        if not months:
            await callback.message.edit_text(text=i18n.get("book_no_windows"))
            await clear_state_keep_hub(state)
        else:
            await show_months(message=callback.message, months=months, i18n=i18n)
        await callback.answer()
        return

    if current == BookingSG.choosing_window.state:
        year = fsm_data.get("book_year")
        month = fsm_data.get("book_month")
        windows = await booking.list_available_windows(
            master_user_id=master_user_id,
            duration_minutes=fsm_data["service_duration"],
            schedule_mode=schedule_mode,
        )
        days = unique_days(windows, bot_timezone)
        if year is not None and month is not None:
            days = days_in_month(days, int(year), int(month))
        await state.set_state(BookingSG.choosing_day)
        await state.update_data(day=None, starts_at=None)
        if not days or year is None or month is None:
            await callback.message.edit_text(text=i18n.get("book_no_windows"))
            await clear_state_keep_hub(state)
        else:
            await show_days(
                message=callback.message,
                year=int(year),
                month=int(month),
                days=days,
                i18n=i18n,
            )
        await callback.answer()
        return

    if current == BookingSG.confirming.state:
        day = date.fromisoformat(fsm_data["day"])
        windows = windows_on_day(
            await booking.list_available_windows(
                master_user_id=master_user_id,
                duration_minutes=fsm_data["service_duration"],
                schedule_mode=schedule_mode,
            ),
            day,
            bot_timezone,
        )
        await state.set_state(BookingSG.choosing_window)
        await state.update_data(starts_at=None)
        if not windows:
            await callback.answer(text=i18n.get("book_no_windows"), show_alert=True)
            return
        await show_windows(
            message=callback.message,
            windows=windows,
            i18n=i18n,
            bot_timezone=bot_timezone,
        )
        await callback.answer()
        return

    await callback.answer()
