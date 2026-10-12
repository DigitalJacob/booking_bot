"""Window selection step for client booking."""

from datetime import date, datetime

from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from app.bot.handlers.client.booking.common import show_confirm, windows_on_day
from app.bot.handlers.client.booking.router import booking_router
from app.bot.keyboards.booking import WindowCallback
from app.bot.states.states import BookingSG
from app.domain.services.booking import BookingService
from app.infrastructure.database.repositories import Repositories


@booking_router.callback_query(
    WindowCallback.filter(),
    StateFilter(BookingSG.choosing_window),
)
async def process_window_choice(
    callback: CallbackQuery,
    callback_data: WindowCallback,
    i18n: dict[str, str],
    state: FSMContext,
    repos: Repositories,
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
        await booking.list_available_windows(
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
    await state.set_state(BookingSG.confirming)
    await show_confirm(
        message=callback.message,
        service=service,
        starts_at=match.starts_at,
        i18n=i18n,
        bot_timezone=bot_timezone,
    )
    await callback.answer()
