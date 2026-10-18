"""Month and day selection steps for client booking."""

from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from app.bot.handlers.client.booking.router import booking_router
from app.bot.handlers.common.booking_funnel import handle_day_choice, handle_month_choice
from app.bot.keyboards.booking import DayCallback, DayPadCallback, MonthCallback
from app.bot.states.states import BookingSG
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
    await handle_month_choice(
        callback=callback,
        callback_data=callback_data,
        state=state,
        repos=repos,
        i18n=i18n,
        bot_timezone=bot_timezone,
        schedule_mode=schedule_mode,
        states=BookingSG,
    )


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
    await handle_day_choice(
        callback=callback,
        callback_data=callback_data,
        state=state,
        repos=repos,
        i18n=i18n,
        bot_timezone=bot_timezone,
        schedule_mode=schedule_mode,
        states=BookingSG,
    )
