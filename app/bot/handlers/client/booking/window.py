"""Window selection step for client booking."""

from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from app.bot.handlers.client.booking.router import booking_router
from app.bot.handlers.common.booking_funnel import handle_window_choice
from app.bot.keyboards.booking import WindowCallback
from app.bot.states.states import BookingSG
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
    await handle_window_choice(
        callback=callback,
        callback_data=callback_data,
        state=state,
        repos=repos,
        i18n=i18n,
        bot_timezone=bot_timezone,
        schedule_mode=schedule_mode,
        states=BookingSG,
    )
