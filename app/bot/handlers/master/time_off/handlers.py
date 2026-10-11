from __future__ import annotations

from datetime import date

from aiogram import F
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.bot.handlers.master.time_off.common import (
    MONTH_KEY,
    show_time_off_prompt,
    today_local,
)
from app.bot.handlers.master.time_off.router import time_off_router
from app.bot.keyboards.time_off import (
    TimeOffDayCallback,
    TimeOffNavCallback,
    TimeOffPadCallback,
    get_time_off_day_calendar_kb,
)
from app.bot.keyboards.work_days import month_label
from app.bot.states.states import TimeOffSG
from app.bot.utils.dates import (
    format_year_month,
    parse_year_month,
    shift_month,
)
from app.bot.utils.format import local_month_bounds
from app.domain.models import User
from app.infrastructure.database.repositories import Repositories


async def show_break_day_calendar(
    *,
    message: Message,
    state: FSMContext,
    repos: Repositories,
    user: User,
    i18n: dict[str, str],
    bot_timezone: str,
) -> None:
    data = await state.get_data()
    parsed = parse_year_month(data.get(MONTH_KEY))
    year = parsed[0] if parsed else None
    month = parsed[1] if parsed else None
    _, _, year, month = local_month_bounds(
        bot_timezone,
        year=year,
        month=month,
    )
    _, _, current_year, current_month = local_month_bounds(bot_timezone)
    if (year, month) < (current_year, current_month):
        year, month = current_year, current_month

    await state.update_data({MONTH_KEY: format_year_month(year, month)})
    await state.set_state(TimeOffSG.choosing_day)

    today = today_local(bot_timezone)
    work_rows = await repos.work_dates.list_month(
        master_user_id=user.user_id,
        year=year,
        month=month,
    )
    open_days = {row.work_date.day for row in work_rows if row.work_date >= today}
    month_text = month_label(year, month, i18n)
    if open_days:
        text = i18n.get("time_off_choose_open_day").format(month=month_text)
    else:
        text = i18n.get("time_off_month_no_open_days").format(month=month_text)

    kb = get_time_off_day_calendar_kb(
        year=year,
        month=month,
        open_days=open_days,
        i18n=i18n,
        is_current_month=(year, month) == (current_year, current_month),
    )
    await show_time_off_prompt(
        message=message,
        state=state,
        text=text,
        i18n=i18n,
        reply_markup=kb,
    )


async def set_break_month(
    *,
    state: FSMContext,
    bot_timezone: str,
    delta_months: int = 0,
    to_current: bool = False,
) -> None:
    _, _, current_year, current_month = local_month_bounds(bot_timezone)
    if to_current:
        year, month = current_year, current_month
    else:
        data = await state.get_data()
        parsed = parse_year_month(data.get(MONTH_KEY))
        year = parsed[0] if parsed else None
        month = parsed[1] if parsed else None
        _, _, year, month = local_month_bounds(
            bot_timezone,
            year=year,
            month=month,
        )
        year, month = shift_month(year, month, delta_months)
        if (year, month) < (current_year, current_month):
            year, month = current_year, current_month
    await state.update_data({MONTH_KEY: format_year_month(year, month)})


@time_off_router.callback_query(
    TimeOffNavCallback.filter(F.action == "month_prev"),
    StateFilter(TimeOffSG.choosing_day),
)
async def process_break_month_prev(
    callback: CallbackQuery,
    state: FSMContext,
    repos: Repositories,
    user: User,
    i18n: dict[str, str],
    bot_timezone: str,
) -> None:
    await set_break_month(
        state=state,
        bot_timezone=bot_timezone,
        delta_months=-1,
    )
    await show_break_day_calendar(
        message=callback.message,
        state=state,
        repos=repos,
        user=user,
        i18n=i18n,
        bot_timezone=bot_timezone,
    )
    await callback.answer()


@time_off_router.callback_query(
    TimeOffNavCallback.filter(F.action == "month_next"),
    StateFilter(TimeOffSG.choosing_day),
)
async def process_break_month_next(
    callback: CallbackQuery,
    state: FSMContext,
    repos: Repositories,
    user: User,
    i18n: dict[str, str],
    bot_timezone: str,
) -> None:
    await set_break_month(
        state=state,
        bot_timezone=bot_timezone,
        delta_months=1,
    )
    await show_break_day_calendar(
        message=callback.message,
        state=state,
        repos=repos,
        user=user,
        i18n=i18n,
        bot_timezone=bot_timezone,
    )
    await callback.answer()


@time_off_router.callback_query(
    TimeOffNavCallback.filter(F.action == "month_current"),
    StateFilter(TimeOffSG.choosing_day),
)
async def process_break_month_current(
    callback: CallbackQuery,
    state: FSMContext,
    repos: Repositories,
    user: User,
    i18n: dict[str, str],
    bot_timezone: str,
) -> None:
    await set_break_month(
        state=state,
        bot_timezone=bot_timezone,
        to_current=True,
    )
    await show_break_day_calendar(
        message=callback.message,
        state=state,
        repos=repos,
        user=user,
        i18n=i18n,
        bot_timezone=bot_timezone,
    )
    await callback.answer()


@time_off_router.callback_query(
    TimeOffDayCallback.filter(),
    StateFilter(TimeOffSG.choosing_day),
)
async def process_break_day(
    callback: CallbackQuery,
    callback_data: TimeOffDayCallback,
    state: FSMContext,
    repos: Repositories,
    user: User,
    i18n: dict[str, str],
    bot_timezone: str,
) -> None:
    try:
        day = date.fromisoformat(callback_data.value)
    except ValueError:
        await callback.answer(
            text=i18n.get("time_off_day_not_work_day"),
            show_alert=True,
        )
        return

    today = today_local(bot_timezone)
    if day < today:
        await callback.answer(
            text=i18n.get("time_off_invalid_past"),
            show_alert=True,
        )
        return

    work_rows = await repos.work_dates.list_month(
        master_user_id=user.user_id,
        year=day.year,
        month=day.month,
    )
    open_dates = {row.work_date for row in work_rows}
    if day not in open_dates:
        await callback.answer(
            text=i18n.get("time_off_day_not_work_day"),
            show_alert=True,
        )
        return

    await state.update_data(hours_day=day.isoformat())
    await state.set_state(TimeOffSG.starts_time)
    await show_time_off_prompt(
        message=callback.message,
        state=state,
        text=i18n.get("time_off_enter_hours_starts"),
        i18n=i18n,
    )
    await callback.answer()


@time_off_router.callback_query(TimeOffPadCallback.filter())
async def process_break_day_pad(callback: CallbackQuery) -> None:
    await callback.answer()
