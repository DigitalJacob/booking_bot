"""Shared ← Back navigation for client and master booking funnels."""

from __future__ import annotations

from datetime import date

from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup
from aiogram.types import CallbackQuery

from app.bot.handlers.common.booking_steps import (
    bookable_months,
    days_in_month,
    show_days,
    show_months,
    show_services,
    show_windows,
    unique_days,
    windows_on_day,
)
from app.bot.utils.hub_nav import clear_state_keep_hub
from app.domain.services.booking import BookingService
from app.infrastructure.database.repositories import Repositories


async def handle_booking_back(
    *,
    callback: CallbackQuery,
    state: FSMContext,
    repos: Repositories,
    i18n: dict[str, str],
    bot_timezone: str,
    schedule_mode: str,
    states: type[StatesGroup],
    ignore_min_lead: bool = False,
) -> None:
    current = await state.get_state()
    fsm_data = await state.get_data()
    master_user_id = fsm_data["master_user_id"]
    booking = BookingService(repos)

    if current == states.choosing_month.state:
        services = await booking.list_services(master_user_id=master_user_id)
        await state.set_state(states.choosing_service)
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

    if current == states.choosing_day.state:
        open_months = await booking.list_open_months(
            master_user_id=master_user_id,
            schedule_mode=schedule_mode,
        )
        windows = await booking.list_available_windows(
            master_user_id=master_user_id,
            duration_minutes=fsm_data["service_duration"],
            schedule_mode=schedule_mode,
            ignore_min_lead=ignore_min_lead,
        )
        months = bookable_months(
            open_months,
            unique_days(windows, bot_timezone),
        )
        await state.set_state(states.choosing_month)
        await state.update_data(day=None, starts_at=None, book_year=None, book_month=None)
        if not months:
            await callback.message.edit_text(text=i18n.get("book_no_windows"))
            await clear_state_keep_hub(state)
        else:
            await show_months(message=callback.message, months=months, i18n=i18n)
        await callback.answer()
        return

    if current == states.choosing_window.state:
        year = fsm_data.get("book_year")
        month = fsm_data.get("book_month")
        windows = await booking.list_available_windows(
            master_user_id=master_user_id,
            duration_minutes=fsm_data["service_duration"],
            schedule_mode=schedule_mode,
            ignore_min_lead=ignore_min_lead,
        )
        days = unique_days(windows, bot_timezone)
        if year is not None and month is not None:
            days = days_in_month(days, int(year), int(month))
        await state.set_state(states.choosing_day)
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

    if current == states.confirming.state:
        day = date.fromisoformat(fsm_data["day"])
        windows = windows_on_day(
            await booking.list_available_windows(
                master_user_id=master_user_id,
                duration_minutes=fsm_data["service_duration"],
                schedule_mode=schedule_mode,
                ignore_min_lead=ignore_min_lead,
            ),
            day,
            bot_timezone,
        )
        await state.set_state(states.choosing_window)
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
