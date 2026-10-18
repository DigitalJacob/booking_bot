"""Shared forward steps for client and master booking funnels."""

from __future__ import annotations

from datetime import date, datetime

from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup
from aiogram.types import CallbackQuery

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
from app.bot.keyboards.booking import (
    DayCallback,
    MonthCallback,
    ServiceCallback,
    WindowCallback,
    get_confirm_kb,
)
from app.domain.models import TimeWindow
from app.domain.services.booking import BookingService
from app.infrastructure.database.repositories import Repositories


async def _list_windows(
    booking: BookingService,
    *,
    master_user_id: int,
    duration_minutes: int,
    schedule_mode: str,
    for_master: bool,
) -> list[TimeWindow]:
    if for_master:
        return await booking.list_windows_for_master(
            master_user_id=master_user_id,
            duration_minutes=duration_minutes,
            schedule_mode=schedule_mode,
        )
    return await booking.list_available_windows(
        master_user_id=master_user_id,
        duration_minutes=duration_minutes,
        schedule_mode=schedule_mode,
    )


async def handle_service_choice(
    *,
    callback: CallbackQuery,
    callback_data: ServiceCallback,
    state: FSMContext,
    repos: Repositories,
    i18n: dict[str, str],
    bot_timezone: str,
    schedule_mode: str,
    states: type[StatesGroup],
    for_master: bool = False,
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
    windows = await _list_windows(
        booking,
        master_user_id=master_user_id,
        duration_minutes=service.duration_minutes,
        schedule_mode=schedule_mode,
        for_master=for_master,
    )
    months = bookable_months(open_months, unique_days(windows, bot_timezone))
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
    await state.set_state(states.choosing_month)
    await show_months(message=callback.message, months=months, i18n=i18n)
    await callback.answer()


async def handle_month_choice(
    *,
    callback: CallbackQuery,
    callback_data: MonthCallback,
    state: FSMContext,
    repos: Repositories,
    i18n: dict[str, str],
    bot_timezone: str,
    schedule_mode: str,
    states: type[StatesGroup],
    for_master: bool = False,
) -> None:
    fsm_data = await state.get_data()
    master_user_id = fsm_data["master_user_id"]
    service_duration = fsm_data["service_duration"]

    booking = BookingService(repos)
    open_months = await booking.list_open_months(
        master_user_id=master_user_id,
        schedule_mode=schedule_mode,
    )
    windows = await _list_windows(
        booking,
        master_user_id=master_user_id,
        duration_minutes=service_duration,
        schedule_mode=schedule_mode,
        for_master=for_master,
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
    await state.set_state(states.choosing_day)
    await show_days(
        message=callback.message,
        year=callback_data.year,
        month=callback_data.month,
        days=days,
        i18n=i18n,
    )
    await callback.answer()


async def handle_day_choice(
    *,
    callback: CallbackQuery,
    callback_data: DayCallback,
    state: FSMContext,
    repos: Repositories,
    i18n: dict[str, str],
    bot_timezone: str,
    schedule_mode: str,
    states: type[StatesGroup],
    for_master: bool = False,
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
        await _list_windows(
            booking,
            master_user_id=master_user_id,
            duration_minutes=service_duration,
            schedule_mode=schedule_mode,
            for_master=for_master,
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
    await state.set_state(states.choosing_window)
    await show_windows(
        message=callback.message,
        windows=windows,
        i18n=i18n,
        bot_timezone=bot_timezone,
    )
    await callback.answer()


async def handle_window_choice(
    *,
    callback: CallbackQuery,
    callback_data: WindowCallback,
    state: FSMContext,
    repos: Repositories,
    i18n: dict[str, str],
    bot_timezone: str,
    schedule_mode: str,
    states: type[StatesGroup],
    for_master: bool = False,
    confirm_header: str | None = None,
    confirm_button_key: str | None = None,
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
        await _list_windows(
            booking,
            master_user_id=master_user_id,
            duration_minutes=service.duration_minutes,
            schedule_mode=schedule_mode,
            for_master=for_master,
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
    await state.set_state(states.confirming)
    reply_markup = None
    if confirm_button_key is not None:
        reply_markup = get_confirm_kb(
            i18n=i18n,
            confirm_button_key=confirm_button_key,
        )
    await show_confirm(
        message=callback.message,
        service=service,
        starts_at=match.starts_at,
        i18n=i18n,
        bot_timezone=bot_timezone,
        header=confirm_header,
        reply_markup=reply_markup,
    )
    await callback.answer()
