"""Month and day selection steps for client booking."""

from datetime import date

from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from app.bot.handlers.client.booking.common import (
    days_in_month,
    show_days,
    show_windows,
    unique_days,
    windows_on_day,
)
from app.bot.handlers.client.booking.router import booking_router
from app.bot.keyboards.booking import DayCallback, DayPadCallback, MonthCallback
from app.bot.states.states import BookingSG
from app.domain.services.booking import BookingService
from app.infrastructure.database.repositories import Repositories


@booking_router.callback_query(
    MonthCallback.filter(),
    StateFilter(BookingSG.choosing_month),
)
async def process_month_choice(
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
    windows = await booking.list_available_windows(
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
    await state.set_state(BookingSG.choosing_day)
    await show_days(
        message=callback.message,
        year=callback_data.year,
        month=callback_data.month,
        days=days,
        i18n=i18n,
    )
    await callback.answer()


@booking_router.callback_query(DayPadCallback.filter())
async def process_day_pad(callback: CallbackQuery) -> None:
    await callback.answer()


@booking_router.callback_query(
    DayCallback.filter(),
    StateFilter(BookingSG.choosing_day),
)
async def process_day_choice(
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
        await booking.list_available_windows(
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
    await state.set_state(BookingSG.choosing_window)
    await show_windows(
        message=callback.message,
        windows=windows,
        i18n=i18n,
        bot_timezone=bot_timezone,
    )
    await callback.answer()
